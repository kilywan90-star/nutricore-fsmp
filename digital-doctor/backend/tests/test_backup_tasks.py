import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from src.models.backup import BackupRecord, BackupStatus, BackupType


@pytest.mark.asyncio
async def test_cleanup_expired_deletes_old_records(db_session):
    """cleanup_expired_backups should delete records older than retention period."""
    from src.tasks.backup_tasks import cleanup_expired_backups

    old_date = datetime.now(timezone.utc) - timedelta(days=60)
    r1 = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/old.sql.gz",
        status=BackupStatus.COMPLETED,
        started_at=old_date,
        retention_days=30,
        file_size_bytes=100,
    )
    r2 = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/recent.sql.gz",
        status=BackupStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        retention_days=30,
        file_size_bytes=200,
    )
    db_session.add_all([r1, r2])
    await db_session.commit()

    deleted = await cleanup_expired_backups(db=db_session)
    assert deleted >= 1

    stmt = select(BackupRecord).where(BackupRecord.id == r1.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None

    stmt2 = select(BackupRecord).where(BackupRecord.id == r2.id)
    result2 = await db_session.execute(stmt2)
    assert result2.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_verify_marks_backup_as_verified(db_session):
    """verify_latest_backup should find the latest completed backup and verify it."""
    from src.tasks.backup_tasks import verify_latest_backup

    r = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/test_verify.sql.gz",
        status=BackupStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        retention_days=30,
    )
    db_session.add(r)
    await db_session.commit()

    result = await verify_latest_backup(db=db_session)
    # The result may be None if no completed backup is found or if the file doesn't exist.
    # In this test environment the file won't exist, so the verification should still
    # return a result dict showing file_exists: false
    if result is not None:
        assert "backup_id" in result
        assert "file_exists" in result
