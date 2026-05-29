import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from news_agent.storage.database import get_connection


@dataclass
class Article:
    url: str
    title_original: str
    source: str
    category: str
    fingerprint: str
    collected_at: datetime
    title_rewritten: Optional[str] = None
    body_rewritten: Optional[str] = None
    image_path: Optional[str] = None
    status: str = "draft"
    id: Optional[int] = None

    def save(self) -> None:
        conn = get_connection()
        conn.execute(
            """INSERT OR REPLACE INTO articles
               (url, title_original, title_rewritten, body_rewritten, image_path,
                source, category, status, fingerprint, collected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self.url, self.title_original, self.title_rewritten,
                self.body_rewritten, self.image_path, self.source,
                self.category, self.status, self.fingerprint,
                self.collected_at.isoformat(),
            ),
        )
        conn.commit()
        if self.id is None:
            row = conn.execute("SELECT last_insert_rowid()").fetchone()
            self.id = row[0]
        conn.close()

    @staticmethod
    def url_exists(url: str) -> bool:
        conn = get_connection()
        row = conn.execute("SELECT 1 FROM articles WHERE url = ?", (url,)).fetchone()
        conn.close()
        return row is not None

    @staticmethod
    def find_by_fingerprint_similar(fingerprint: str, threshold_bits: int = 10) -> bool:
        conn = get_connection()
        rows = conn.execute("SELECT fingerprint FROM fingerprints").fetchall()
        conn.close()
        for (fp,) in rows:
            if _hamming_distance(int(fingerprint), int(fp)) <= threshold_bits:
                return True
        return False


def _hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@dataclass
class RunLog:
    run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    collected: int = 0
    after_dedup: int = 0
    generated: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    status: str = "success"
    id: Optional[int] = None

    def save(self) -> None:
        conn = get_connection()
        conn.execute(
            """INSERT INTO run_log (run_at, collected, after_dedup, generated, failed, errors, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                self.run_at.isoformat(), self.collected, self.after_dedup,
                self.generated, self.failed, json.dumps(self.errors, ensure_ascii=False),
                self.status,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT last_insert_rowid()").fetchone()
        self.id = row[0]
        conn.close()


def insert_fingerprint(fingerprint: str, url: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO fingerprints (fingerprint, url) VALUES (?, ?)",
        (fingerprint, url),
    )
    conn.commit()
    conn.close()
