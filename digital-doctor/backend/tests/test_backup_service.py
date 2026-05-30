import pytest
import uuid
from sqlalchemy import select, func
from src.models.backup import BackupRecord, BackupStatus, BackupType
from src.services.backup_service import list_backups, verify_backup, get_backup_stats


@pytest.mark.asyncio
async def test_create_backup_record(db_session):
    """Creating a backup record should persist to the database."""
    from src.services.backup_service import create_backup

    # We create a minimal record directly since pg_dump won't work in test
    record = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/test_backup.sql.gz",
        file_size_bytes=1024,
        checksum_sha256="a" * 64,
        status=BackupStatus.COMPLETED,
        retention_days=30,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
    assert record.backup_type == BackupType.FULL
    assert record.status == BackupStatus.COMPLETED
    assert record.file_size_bytes == 1024

    stmt = select(BackupRecord).where(BackupRecord.id == record.id)
    result = await db_session.execute(stmt)
    loaded = result.scalar_one()
    assert loaded.file_path == "/app/backups/test_backup.sql.gz"


@pytest.mark.asyncio
async def test_list_backups(db_session):
    """list_backups should return records ordered by started_at descending."""
    r1 = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/b1.sql.gz",
        status=BackupStatus.COMPLETED,
        retention_days=30,
    )
    r2 = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.INCREMENTAL,
        file_path="/app/backups/b2.sql.gz",
        status=BackupStatus.FAILED,
        retention_days=30,
    )
    db_session.add_all([r1, r2])
    await db_session.commit()

    records = await list_backups(db_session, limit=50)
    assert len(records) >= 2
    assert records[0].started_at >= records[1].started_at


@pytest.mark.asyncio
async def test_verify_backup(db_session):
    """verify_backup should return a result dict and mark the record as verified."""
    record = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/nonexistent/backup.sql.gz",
        status=BackupStatus.COMPLETED,
        retention_days=30,
    )
    db_session.add(record)
    await db_session.commit()

    result = await verify_backup(record.id, db_session)
    assert result["backup_id"] == str(record.id)
    assert "file_exists" in result
    assert result["file_exists"] is False


@pytest.mark.asyncio
async def test_get_backup_stats(db_session):
    """get_backup_stats should return aggregate statistics."""
    r1 = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/b1.sql.gz",
        file_size_bytes=1000,
        status=BackupStatus.COMPLETED,
        retention_days=30,
    )
    r2 = BackupRecord(
        id=uuid.uuid4(),
        backup_type=BackupType.FULL,
        file_path="/app/backups/b2.sql.gz",
        file_size_bytes=2000,
        status=BackupStatus.FAILED,
        retention_days=30,
    )
    db_session.add_all([r1, r2])
    await db_session.commit()

    stats = await get_backup_stats(db_session)
    assert stats["total_backups"] >= 2
    assert stats["successful_backups"] >= 1
    assert stats["failed_backups"] >= 1
    assert stats["total_size_bytes"] >= 3000
    assert 0 <= stats["success_rate"] <= 100
