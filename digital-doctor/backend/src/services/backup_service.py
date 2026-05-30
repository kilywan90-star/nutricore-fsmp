"""Backup service — create, list, verify backups and compute statistics."""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.backup import BackupRecord, BackupStatus, BackupType


BACKUP_DIR = Path("backups")


def _compute_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


async def create_backup(backup_type: str, db: AsyncSession) -> BackupRecord:
    """Initiate a backup and store the record. Returns the record after completion."""
    bt = BackupType(backup_type)

    record = BackupRecord(
        id=uuid.uuid4(),
        backup_type=bt,
        file_path="",
        status=BackupStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
        retention_days=settings.BACKUP_RETENTION_DAYS,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{bt.value}_{timestamp}.sql.gz"

        import subprocess

        temp_path = BACKUP_DIR / f"temp_{record.id}.sql"
        env = os.environ.copy()
        env["PGPASSWORD"] = "ddd_secret_dev"
        subprocess.run(
            [
                "pg_dump",
                "-h", "db",
                "-U", "ddd",
                "-d", "digital_doctor",
                "-f", str(temp_path),
            ],
            env=env,
            check=True,
            capture_output=True,
        )

        import gzip
        dest_path = BACKUP_DIR / filename
        with open(temp_path, "rb") as f_in:
            with gzip.open(dest_path, "wb") as f_out:
                f_out.writelines(f_in)
        temp_path.unlink(missing_ok=True)

        record.file_path = str(dest_path.absolute())
        record.file_size_bytes = dest_path.stat().st_size
        record.checksum_sha256 = _compute_sha256(str(dest_path))
        record.status = BackupStatus.COMPLETED
        record.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        record.status = BackupStatus.FAILED
        record.error_message = str(exc)[:1000]
        record.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(record)
    return record


async def list_backups(db: AsyncSession, limit: int = 50) -> list[BackupRecord]:
    """List recent backups, newest first."""
    stmt = (
        select(BackupRecord)
        .order_by(desc(BackupRecord.started_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def verify_backup(backup_id: uuid.UUID, db: AsyncSession) -> dict:
    """Verify backup integrity: checksum, file exists, size matches."""
    stmt = select(BackupRecord).where(BackupRecord.id == backup_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        return {"backup_id": str(backup_id), "error": "Backup record not found"}

    info: dict = {
        "backup_id": str(record.id),
        "file_path": record.file_path,
        "status": record.status.value,
        "checksum_match": None,
        "file_exists": False,
        "size_match": None,
    }

    if not record.file_path or not Path(record.file_path).exists():
        return info

    info["file_exists"] = True
    actual_size = Path(record.file_path).stat().st_size
    info["actual_size_bytes"] = actual_size
    info["recorded_size_bytes"] = record.file_size_bytes
    info["size_match"] = actual_size == record.file_size_bytes

    if record.checksum_sha256:
        try:
            actual_checksum = _compute_sha256(record.file_path)
            info["actual_checksum"] = actual_checksum
            info["recorded_checksum"] = record.checksum_sha256
            info["checksum_match"] = actual_checksum == record.checksum_sha256
        except Exception:
            info["checksum_match"] = False

    info["verified"] = info.get("checksum_match", False) and info.get("file_exists", False)

    if info.get("verified"):
        record.status = BackupStatus.VERIFIED
        await db.commit()

    return info


async def get_backup_stats(db: AsyncSession) -> dict:
    """Return aggregate backup statistics."""
    total_stmt = select(func.count(BackupRecord.id))
    total_result = await db.execute(total_stmt)
    total_backups = total_result.scalar() or 0

    size_stmt = select(func.coalesce(func.sum(BackupRecord.file_size_bytes), 0)).where(
        BackupRecord.file_size_bytes.isnot(None)
    )
    size_result = await db.execute(size_stmt)
    total_size = size_result.scalar() or 0

    success_stmt = select(func.count(BackupRecord.id)).where(
        BackupRecord.status.in_([BackupStatus.COMPLETED, BackupStatus.VERIFIED])
    )
    success_result = await db.execute(success_stmt)
    successful = success_result.scalar() or 0

    success_rate = (successful / total_backups * 100) if total_backups > 0 else 0.0

    last_stmt = (
        select(BackupRecord.completed_at)
        .where(BackupRecord.status.in_([BackupStatus.COMPLETED, BackupStatus.VERIFIED]))
        .order_by(desc(BackupRecord.completed_at))
        .limit(1)
    )
    last_result = await db.execute(last_stmt)
    last_successful = last_result.scalar_one_or_none()

    return {
        "total_backups": total_backups,
        "total_size_bytes": total_size,
        "successful_backups": successful,
        "failed_backups": total_backups - successful,
        "success_rate": round(success_rate, 2),
        "last_successful_at": last_successful.isoformat() if last_successful else None,
    }
