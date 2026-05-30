"""Offline queue — SQLite-backed action queue for grassroots deployments.

When the device is offline, actions are queued locally. On reconnect,
the queue is processed against the main server database.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class OfflineQueue:
    """SQLite-backed queue for grassroots offline action buffering.

    Actions: screening, follow-up, glucose records entered while offline.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(Path(__file__).resolve().parent.parent.parent / "offline_queue.db")
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offline_queue (
                id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT,
                created_at TEXT NOT NULL,
                synced_at TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def enqueue(self, action: str, data: dict) -> str:
        """Queue an action for later sync. Returns the queue entry ID."""
        conn = self._get_conn()
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO offline_queue (id, action, data, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, action, json.dumps(data, default=str), "pending", now),
        )
        conn.commit()
        logger.info("OfflineQueue: enqueued action=%s id=%s", action, entry_id)
        return entry_id

    def process_queue(self, db_session) -> dict[str, Any]:
        """Process all pending queue items against the main server DB session.

        Returns dict with counts of synced/failed items.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, action, data FROM offline_queue WHERE status = 'pending' ORDER BY created_at"
        ).fetchall()

        synced = 0
        failed = 0
        errors: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()

        for row in rows:
            try:
                data = json.loads(row["data"])
                self._process_action(row["id"], row["action"], data, db_session, conn, now)
                synced += 1
            except Exception as exc:
                failed += 1
                error_msg = str(exc)
                errors.append({"id": row["id"], "action": row["action"], "error": error_msg})
                conn.execute(
                    "UPDATE offline_queue SET status = 'failed', error = ? WHERE id = ?",
                    (error_msg, row["id"]),
                )
                logger.error("OfflineQueue: failed to process id=%s: %s", row["id"], error_msg)

        conn.commit()
        return {"synced": synced, "failed": failed, "errors": errors}

    def _process_action(
        self,
        entry_id: str,
        action: str,
        data: dict,
        db_session,
        conn: sqlite3.Connection,
        now: str,
    ) -> None:
        """Dispatch a single queue action to the appropriate handler."""
        from src.models.grassroots import (
            GrassrootsPatient,
            GrassrootsScreening,
            GrassrootsFollowUp,
            RiskLevel,
            ReferralStatus,
        )

        if action == "screening":
            screening = GrassrootsScreening(
                patient_id=uuid.UUID(data["patient_id"]),
                age=data["age"],
                gender=data["gender"],
                waist_circumference=data["waist_circumference"],
                fasting_glucose=data["fasting_glucose"],
                systolic_bp=data.get("systolic_bp", 120),
                diastolic_bp=data.get("diastolic_bp", 80),
                family_history=data.get("family_history", False),
                risk_level=RiskLevel(data["risk_level"]),
                risk_score=data["risk_score"],
                referral_needed=data.get("referral_needed", False),
                referral_status=ReferralStatus(data.get("referral_status", "none")),
                recommendation=data.get("recommendation", ""),
                screened_at=datetime.fromisoformat(data["screened_at"]) if "screened_at" in data else datetime.utcnow(),
                synced=True,
            )
            db_session.add(screening)

        elif action == "follow_up":
            fu = GrassrootsFollowUp(
                patient_id=uuid.UUID(data["patient_id"]),
                glucose_value=data.get("glucose_value"),
                medication_adherent=data.get("medication_adherent"),
                new_symptoms=data.get("new_symptoms"),
                referral_needed=data.get("referral_needed", False),
                referral_reason=data.get("referral_reason"),
                notes=data.get("notes"),
                followed_up_at=datetime.fromisoformat(data["followed_up_at"]) if "followed_up_at" in data else datetime.utcnow(),
                synced=True,
            )
            if "next_follow_up" in data and data["next_follow_up"]:
                from datetime import date as date_type
                fu.next_follow_up = date_type.fromisoformat(data["next_follow_up"])
            db_session.add(fu)

        elif action == "patient":
            gp = GrassrootsPatient(
                id=uuid.UUID(data["id"]),
                name=data["name"],
                village=data["village"],
                gender=data["gender"],
                birth_year=data["birth_year"],
                diabetes_type=data.get("diabetes_type"),
                hospital_id=uuid.UUID(data["hospital_id"]) if data.get("hospital_id") else None,
            )
            db_session.add(gp)

        else:
            raise ValueError(f"Unknown action type: {action}")

        conn.execute(
            "UPDATE offline_queue SET status = 'synced', synced_at = ? WHERE id = ?",
            (now, entry_id),
        )

    def get_queue_status(self) -> dict[str, Any]:
        """Return current queue status: pending count, last sync time, errors."""
        conn = self._get_conn()
        pending = conn.execute(
            "SELECT COUNT(*) as cnt FROM offline_queue WHERE status = 'pending'"
        ).fetchone()["cnt"]
        failed_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM offline_queue WHERE status = 'failed'"
        ).fetchone()["cnt"]
        last_synced = conn.execute(
            "SELECT synced_at FROM offline_queue WHERE status = 'synced' ORDER BY synced_at DESC LIMIT 1"
        ).fetchone()

        recent_errors = conn.execute(
            "SELECT id, action, error FROM offline_queue WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10"
        ).fetchall()

        return {
            "pending_count": pending,
            "failed_count": failed_count,
            "last_sync_time": last_synced["synced_at"] if last_synced else None,
            "recent_errors": [{"id": r["id"], "action": r["action"], "error": r["error"]} for r in recent_errors],
        }

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
