import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from news_agent.config import config

DB_PATH = Path(config.pipeline.db_path)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT UNIQUE NOT NULL,
    title_original  TEXT NOT NULL,
    title_rewritten TEXT,
    body_rewritten  TEXT,
    image_path      TEXT,
    source          TEXT NOT NULL,
    category        TEXT NOT NULL CHECK(category IN ('finance', 'ai', 'other')),
    status          TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'published', 'failed')),
    fingerprint     TEXT NOT NULL,
    collected_at    TIMESTAMP NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_articles_fingerprint ON articles(fingerprint);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_collected_at ON articles(collected_at);

CREATE TABLE IF NOT EXISTS fingerprints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT UNIQUE NOT NULL,
    url         TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_fingerprints_hash ON fingerprints(fingerprint);
CREATE INDEX IF NOT EXISTS idx_fingerprints_created ON fingerprints(created_at);

CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TIMESTAMP NOT NULL,
    collected   INTEGER NOT NULL DEFAULT 0,
    after_dedup INTEGER NOT NULL DEFAULT 0,
    generated   INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0,
    errors      TEXT,
    status      TEXT NOT NULL CHECK(status IN ('success', 'partial', 'failed'))
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def cleanup_old_fingerprints(ttl_days: int = 30) -> int:
    conn = get_connection()
    cutoff = datetime.now(timezone.utc)
    cursor = conn.execute(
        "DELETE FROM fingerprints WHERE created_at < datetime(?, ?)",
        (cutoff.isoformat(), f"-{ttl_days} days"),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted
