"""
Database query optimization utilities.

Provides on-demand index creation and slow-query analysis for the
digital-doctor application. Call `add_indexes()` during startup or
migration to ensure critical query paths are covered by database indexes.

Usage:
    from src.db.optimize import add_indexes, analyze_slow_queries

    async with engine.connect() as conn:
        await add_indexes(conn)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

logger = logging.getLogger("performance.db")

# ---------------------------------------------------------------------------
# Index definitions
# ---------------------------------------------------------------------------
# Each entry: (table_name, index_name, column_expression)
# Column expressions use PostgreSQL index syntax (e.g. "patient_id, recorded_at DESC").
# IF NOT EXISTS makes these safe to run repeatedly.

INDEXES = [
    # Glucose records — fast lookups by patient + time ordered
    (
        "glucose_records",
        "ix_glucose_records_patient_recorded",
        "patient_id, recorded_at DESC",
    ),
    # Ensure the patient_id index exists separately for FK joins
    (
        "glucose_records",
        "ix_glucose_records_patient_id",
        "patient_id",
    ),
    # Alerts — find unacknowledged alerts per patient, ordered by recency
    (
        "alerts",
        "ix_alerts_patient_ack_created",
        "patient_id, acknowledged, created_at DESC",
    ),
    # Lab reports — per-patient report history, ordered by report date
    (
        "lab_reports",
        "ix_lab_reports_patient_report_date",
        "patient_id, report_date DESC",
    ),
    # Medication reminders — active reminders for a given patient
    (
        "medication_reminders",
        "ix_medication_reminders_patient_active",
        "patient_id, is_active",
    ),
    # Notifications — fast lookup by user_id + status
    (
        "notifications",
        "ix_notifications_user_status",
        "user_id, status, scheduled_at DESC",
    ),
    # User lookups by role (for admin/department queries)
    (
        "users",
        "ix_users_role_active",
        "role, is_active",
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def add_indexes(conn: AsyncConnection | None = None) -> list[str]:
    """Create recommended indexes that are missing.

    If `conn` is not provided, a new connection is created from the global engine.
    Returns a list of index names that were created.
    """
    created: list[str] = []

    if conn is None:
        from src.db.session import engine

        async with engine.begin() as conn:
            return await _create_indexes(conn, created)

    return await _create_indexes(conn, created)


async def _create_indexes(conn: AsyncConnection, created: list[str]) -> list[str]:
    for table_name, index_name, columns in INDEXES:
        ddl = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns})"
        try:
            await conn.execute(text(ddl))
            created.append(index_name)
            logger.debug("Index %s created on %s (%s)", index_name, table_name, columns)
        except Exception as exc:
            logger.warning("Failed to create index %s: %s", index_name, exc)

    return created


async def analyze_slow_queries(
    db: AsyncSession,
    threshold_ms: float = 100.0,
    *,
    log_results: bool = True,
    explain_fn: Callable[..., Any] | None = None,
) -> list[dict[str, Any]]:
    """Identify and explain active queries exceeding the latency threshold.

    Queries PostgreSQL's `pg_stat_activity` for currently running queries
    that have been executing longer than `threshold_ms`. For each slow query,
    runs EXPLAIN ANALYZE to capture the execution plan.

    Returns a list of dicts with:
        - pid: process ID
        - query: truncated SQL text
        - duration_ms: how long the query has been running
        - explain_plan: summary of the EXPLAIN output (if available)

    This is diagnostic tooling. In production, prefer pg_stat_statements for
    historical query analysis.
    """
    slow_queries: list[dict[str, Any]] = []
    explain_fn = explain_fn or _default_explain

    try:
        # Query for long-running statements on the current database
        activity_sql = text("""
            SELECT
                pid,
                query,
                EXTRACT(EPOCH FROM (NOW() - query_start)) * 1000 AS duration_ms,
                state
            FROM pg_stat_activity
            WHERE
                state = 'active'
                AND query NOT LIKE '%pg_stat_activity%'
                AND query_start IS NOT NULL
                AND EXTRACT(EPOCH FROM (NOW() - query_start)) * 1000 > :threshold_ms
            ORDER BY duration_ms DESC
        """)

        result = await db.execute(activity_sql, {"threshold_ms": threshold_ms})
        rows = result.fetchall()

        for row in rows:
            entry = {
                "pid": row.pid,
                "query": row.query[:500] if row.query else "<unknown>",
                "duration_ms": round(row.duration_ms, 1),
                "state": row.state,
            }
            try:
                explain_plan = await explain_fn(db, entry["query"])
                entry["explain_plan"] = explain_plan
            except Exception as exc:
                entry["explain_plan"] = f"EXPLAIN failed: {exc}"

            if log_results:
                logger.warning(
                    "SLOW QUERY [pid=%s, %s ms]: %s",
                    entry["pid"],
                    entry["duration_ms"],
                    entry["query"][:200],
                )

            slow_queries.append(entry)

    except Exception as exc:
        logger.error("analyze_slow_queries failed: %s", exc)

    return slow_queries


async def _default_explain(db: AsyncSession, query: str) -> str:
    """Run EXPLAIN ANALYZE on a query and return a brief summary."""
    # Only EXPLAIN (not ANALYZE) for safety — ANALYZE actually executes the query
    explain_sql = text(f"EXPLAIN (FORMAT TEXT, COSTS TRUE, BUFFERS TRUE) {query}")
    try:
        result = await db.execute(explain_sql)
        rows = result.fetchmany(5)
        return "\n".join(row[0] for row in rows if row[0])
    except Exception:
        return "EXPLAIN not available for this statement"


async def get_index_info(db: AsyncSession, table_name: str | None = None) -> list[dict[str, Any]]:
    """Return index metadata for a specific table or all user tables.

    Useful for verifying which indexes exist before and after calling add_indexes().
    """
    if table_name:
        sql = text("""
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = :table_name
            ORDER BY indexname
        """)
        result = await db.execute(sql, {"table_name": table_name})
    else:
        sql = text("""
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        result = await db.execute(sql)

    rows = result.fetchall()
    return [
        {"table": row.tablename, "index": row.indexname, "definition": row.indexdef}
        for row in rows
    ]
