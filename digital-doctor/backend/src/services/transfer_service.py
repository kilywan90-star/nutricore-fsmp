"""Cross-hospital patient transfer service."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.org import TransferRecord, TransferStatus, Hospital


async def request_transfer(
    db: AsyncSession,
    patient_id: uuid.UUID,
    from_hospital_id: uuid.UUID,
    to_hospital_id: uuid.UUID,
    requested_by: uuid.UUID,
    reason: str | None = None,
) -> dict[str, Any]:
    """Initiate a patient transfer request."""
    if from_hospital_id == to_hospital_id:
        raise ValueError("Cannot transfer to the same hospital")

    # Verify both hospitals exist and are active
    from_hosp_stmt = select(Hospital).where(
        Hospital.id == from_hospital_id,
        Hospital.is_active == True,
    )
    from_hosp = (await db.execute(from_hosp_stmt)).scalar_one_or_none()
    if not from_hosp:
        raise ValueError(f"Source hospital not found or inactive: {from_hospital_id}")

    to_hosp_stmt = select(Hospital).where(
        Hospital.id == to_hospital_id,
        Hospital.is_active == True,
    )
    to_hosp = (await db.execute(to_hosp_stmt)).scalar_one_or_none()
    if not to_hosp:
        raise ValueError(f"Target hospital not found or inactive: {to_hospital_id}")

    transfer = TransferRecord(
        patient_id=patient_id,
        from_hospital_id=from_hospital_id,
        to_hospital_id=to_hospital_id,
        requested_by=requested_by,
        status=TransferStatus.PENDING,
        reason=reason,
    )
    db.add(transfer)
    await db.commit()
    await db.refresh(transfer)

    return {
        "id": str(transfer.id),
        "patient_id": str(transfer.patient_id),
        "from_hospital_id": str(transfer.from_hospital_id),
        "from_hospital_name": from_hosp.name,
        "to_hospital_id": str(transfer.to_hospital_id),
        "to_hospital_name": to_hosp.name,
        "status": transfer.status.value,
        "reason": transfer.reason,
        "created_at": transfer.created_at.isoformat(),
    }


async def approve_transfer(
    db: AsyncSession,
    transfer_id: uuid.UUID,
    approved_by: uuid.UUID,
) -> dict[str, Any]:
    """Approve a pending transfer (called by receiving hospital)."""
    stmt = select(TransferRecord).where(TransferRecord.id == transfer_id)
    result = await db.execute(stmt)
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise ValueError(f"Transfer not found: {transfer_id}")

    if transfer.status != TransferStatus.PENDING:
        raise ValueError(f"Transfer is not in pending status: {transfer.status.value}")

    transfer.status = TransferStatus.APPROVED
    transfer.approved_by = approved_by
    transfer.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(transfer)

    return {
        "id": str(transfer.id),
        "patient_id": str(transfer.patient_id),
        "from_hospital_id": str(transfer.from_hospital_id),
        "to_hospital_id": str(transfer.to_hospital_id),
        "status": transfer.status.value,
        "approved_by": str(approved_by),
        "updated_at": transfer.updated_at.isoformat() if transfer.updated_at else None,
    }


async def reject_transfer(
    db: AsyncSession,
    transfer_id: uuid.UUID,
    rejected_by: uuid.UUID,
) -> dict[str, Any]:
    """Reject a pending transfer."""
    stmt = select(TransferRecord).where(TransferRecord.id == transfer_id)
    result = await db.execute(stmt)
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise ValueError(f"Transfer not found: {transfer_id}")

    if transfer.status != TransferStatus.PENDING:
        raise ValueError(f"Transfer is not in pending status: {transfer.status.value}")

    transfer.status = TransferStatus.REJECTED
    transfer.approved_by = rejected_by
    transfer.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(transfer)

    return {
        "id": str(transfer.id),
        "patient_id": str(transfer.patient_id),
        "from_hospital_id": str(transfer.from_hospital_id),
        "to_hospital_id": str(transfer.to_hospital_id),
        "status": transfer.status.value,
        "rejected_by": str(rejected_by),
        "updated_at": transfer.updated_at.isoformat() if transfer.updated_at else None,
    }


async def list_transfers(
    db: AsyncSession,
    hospital_id: uuid.UUID | None = None,
    status_filter: TransferStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List transfer records, optionally scoped to a hospital."""
    from sqlalchemy import func

    query = select(TransferRecord)
    if hospital_id:
        query = query.where(
            (TransferRecord.from_hospital_id == hospital_id)
            | (TransferRecord.to_hospital_id == hospital_id)
        )
    if status_filter:
        query = query.where(TransferRecord.status == status_filter)

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    query = query.order_by(desc(TransferRecord.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    transfers = result.scalars().all()

    items = []
    for t in transfers:
        # Resolve hospital names
        from_hosp = (await db.execute(select(Hospital).where(Hospital.id == t.from_hospital_id))).scalar_one_or_none()
        to_hosp = (await db.execute(select(Hospital).where(Hospital.id == t.to_hospital_id))).scalar_one_or_none()

        items.append({
            "id": str(t.id),
            "patient_id": str(t.patient_id),
            "from_hospital_id": str(t.from_hospital_id),
            "from_hospital_name": from_hosp.name if from_hosp else "",
            "to_hospital_id": str(t.to_hospital_id),
            "to_hospital_name": to_hosp.name if to_hosp else "",
            "requested_by": str(t.requested_by),
            "approved_by": str(t.approved_by) if t.approved_by else None,
            "status": t.status.value,
            "reason": t.reason,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}
