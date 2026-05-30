"""Automated backup tasks — daily full, hourly incremental, verify, cleanup."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.backup import BackupRecord, BackupStatus, BackupType
from src.services.backup_service import BACKUP_DIR, _compute_sha256
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)


async def daily_full_backup(db: AsyncSession | None = None) -> BackupRecord | None:
    """Run full database backup via pg_dump, compress, store with timestamp."""
    try:
        if db is not None:
            from src.services.backup_service import create_backup
            record = await create_backup(BackupType.FULL.value, db)
            logger.info("Daily full backup completed: %s", record.id)
            return record
        else:
            async with async_session_factory() as session:
                from src.services.backup_service import create_backup
                record = await create_backup(BackupType.FULL.value, session)
                logger.info("Daily full backup completed: %s", record.id)
                return record
    except Exception as exc:
        logger.exception("Daily full backup failed: %s", exc)
        return None


async def hourly_incremental_backup() -> None:
    """Archive WAL segments for point-in-time recovery.

    For PostgreSQL, this switches the current WAL segment so it is ready
    for archiving. The actual archiving is configured via archive_command
    in postgresql.conf, not performed here.
    """
    try:
        import subprocess
        import os

        env = os.environ.copy()
        env["PGPASSWORD"] = "ddd_secret_dev"
        subprocess.run(
            [
                "psql",
                "-h", "db",
                "-U", "ddd",
                "-d", "digital_doctor",
                "-c", "SELECT pg_switch_wal();",
            ],
            env=env,
            check=True,
            capture_output=True,
            timeout=30,
        )
        logger.info("WAL switch completed for incremental backup")
    except Exception as exc:
        logger.warning("Hourly incremental (WAL switch) skipped: %s", exc)


async def verify_latest_backup(db: AsyncSession | None = None) -> dict | None:
    """Verify checksum of the latest completed full backup."""
    try:
        async def _verify(session: AsyncSession):
            stmt = (
                select(BackupRecord)
                .where(
                    BackupRecord.backup_type == BackupType.FULL,
                    BackupRecord.status == BackupStatus.COMPLETED,
                )
                .order_by(BackupRecord.completed_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if not record:
                logger.info("No completed backup to verify")
                return None

            from src.services.backup_service import verify_backup

            info = await verify_backup(record.id, session)
            logger.info("Backup verification result: %s", info)
            return info

        if db is not None:
            return await _verify(db)
        else:
            async with async_session_factory() as session:
                return await _verify(session)
    except Exception as exc:
        logger.exception("Backup verification failed: %s", exc)
        return None


async def cleanup_expired_backups(db: AsyncSession | None = None) -> int:
    """Delete backup records and files older than retention period."""
    deleted_count = 0
    try:
        async def _cleanup(session: AsyncSession) -> int:
            deleted = 0
            cutoff = datetime.now(timezone.utc)

            stmt = select(BackupRecord).where(
                BackupRecord.started_at < cutoff
            )
            result = await session.execute(stmt)
            all_records = list(result.scalars().all())

            import os
            from pathlib import Path

            for record in all_records:
                age_days = (cutoff - record.started_at).days
                if age_days <= record.retention_days:
                    continue

                if record.file_path:
                    p = Path(record.file_path)
                    if p.exists():
                        p.unlink(missing_ok=True)

                await session.delete(record)
                deleted += 1

            await session.commit()
            logger.info("Cleaned up %d expired backups", deleted)
            return deleted

        if db is not None:
            return await _cleanup(db)
        else:
            async with async_session_factory() as session:
                return await _cleanup(session)
    except Exception as exc:
        logger.exception("Backup cleanup failed: %s", exc)
        return deleted_count
