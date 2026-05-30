"""Backup API — admin-only endpoints for managing database backups."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth_deps import get_current_user, require_role
from src.db.session import get_db
from src.models.user import User
from src.services.backup_service import (
    create_backup,
    list_backups,
    verify_backup,
    get_backup_stats,
)

router = APIRouter()

require_admin = require_role("admin")


@router.post("")
async def trigger_backup(
    backup_type: str = Query(default="full", pattern="^(full|incremental)$"),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    record = await create_backup(backup_type, db)
    return {
        "id": str(record.id),
        "backup_type": record.backup_type.value,
        "status": record.status.value,
        "file_path": record.file_path,
        "file_size_bytes": record.file_size_bytes,
        "checksum_sha256": record.checksum_sha256,
        "started_at": record.started_at.isoformat(),
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "error_message": record.error_message,
    }


@router.get("")
async def list_all_backups(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    records = await list_backups(db, limit=limit)
    return [
        {
            "id": str(r.id),
            "backup_type": r.backup_type.value,
            "file_path": r.file_path,
            "file_size_bytes": r.file_size_bytes,
            "checksum_sha256": r.checksum_sha256,
            "status": r.status.value,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error_message": r.error_message,
            "retention_days": r.retention_days,
        }
        for r in records
    ]


@router.get("/stats")
async def backup_statistics(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_backup_stats(db)


@router.get("/{backup_id}/verify")
async def verify_single_backup(
    backup_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid

    try:
        bid = _uuid.UUID(backup_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid backup ID format")

    result = await verify_backup(bid, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
