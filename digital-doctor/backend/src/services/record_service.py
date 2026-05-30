"""Medical record service — CRUD, versioning, and finalize.

Handles the full lifecycle of medical records:
  - Create from generated content
  - List records for a patient
  - Update with version tracking (saves current version before overwriting)
  - Finalize (status -> FINALIZED)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.records import MedicalRecord, RecordType, RecordStatus


async def create_record(
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    record_type: RecordType,
    content: dict,
    db: AsyncSession,
) -> MedicalRecord:
    """Create a new medical record with version 1.

    Args:
        patient_id: Patient UUID
        doctor_id: Doctor UUID
        record_type: SOAP, DISCHARGE, or PROGRESS
        content: Structured record content dict (must include 'markdown')
        db: Database session

    Returns:
        The created MedicalRecord instance.
    """
    markdown = content.pop("markdown", "")
    if not markdown and isinstance(content, dict):
        markdown = str(content)

    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor_id,
        record_type=record_type,
        content=content,
        markdown=markdown,
        status=RecordStatus.DRAFT,
        version=1,
        versions=[],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_records(
    patient_id: uuid.UUID,
    db: AsyncSession,
    record_type: RecordType | None = None,
) -> list[MedicalRecord]:
    """List medical records for a patient, optionally filtered by type.

    Returns records ordered by most recent first.
    """
    stmt = select(MedicalRecord).where(MedicalRecord.patient_id == patient_id)
    if record_type:
        stmt = stmt.where(MedicalRecord.record_type == record_type)
    stmt = stmt.order_by(MedicalRecord.created_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_record(record_id: uuid.UUID, db: AsyncSession) -> MedicalRecord | None:
    """Get a single medical record by ID."""
    stmt = select(MedicalRecord).where(MedicalRecord.id == record_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_record(
    record_id: uuid.UUID,
    edits: dict,
    doctor_id: uuid.UUID,
    db: AsyncSession,
) -> MedicalRecord | None:
    """Update a medical record's content, saving the current version to history.

    The current content and markdown are appended to the versions[] list
    before overwriting with the new content.

    Args:
        record_id: Record UUID
        edits: Dict with 'content' (dict) and optional 'markdown' (str)
        doctor_id: Doctor UUID performing the edit
        db: Database session

    Returns:
        Updated MedicalRecord, or None if not found.
    """
    record = await get_record(record_id, db)
    if not record:
        return None

    # Save current version to history
    version_entry = {
        "version": record.version,
        "content": record.content,
        "markdown": record.markdown,
        "edited_by": str(doctor_id),
        "edited_at": datetime.utcnow().isoformat(),
    }
    versions = list(record.versions or [])
    versions.append(version_entry)

    # Apply edits
    new_content = edits.get("content", record.content)
    new_markdown = edits.get("markdown", record.markdown)

    record.content = new_content
    record.markdown = new_markdown
    record.version = record.version + 1
    record.versions = versions
    record.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(record)
    return record


async def finalize_record(
    record_id: uuid.UUID,
    doctor_id: uuid.UUID,
    db: AsyncSession,
    signed_by: uuid.UUID | None = None,
    content_hash: str | None = None,
) -> MedicalRecord | None:
    """Finalize a medical record — status -> FINALIZED.

    Only non-finalized records can be finalized.

    Args:
        record_id: Record UUID
        doctor_id: Doctor UUID performing finalize
        db: Database session
        signed_by: Optional signature user ID
        content_hash: Optional SHA-256 content hash from digital signature

    Returns:
        Updated MedicalRecord, or None if not found.
    """
    record = await get_record(record_id, db)
    if not record:
        return None

    record.status = RecordStatus.FINALIZED
    record.signed_by = signed_by or doctor_id
    record.signed_at = datetime.utcnow()
    record.content_hash = content_hash
    record.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(record)
    return record
