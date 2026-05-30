"""Operation audit trail — writes structured audit records to DB."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.org import OperationLog


VALID_ACTIONS = {"VIEW", "CREATE", "UPDATE", "DELETE", "ASSIGN", "EXPORT"}
VALID_RESOURCE_TYPES = {"patient", "medication", "report", "alert", "department", "doctor_profile"}


async def log_operation(
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    details: dict | None,
    db: AsyncSession,
    ip_address: str | None = None,
) -> OperationLog:
    """Write an audit record to the database.

    Args:
        user_id: The user performing the operation (None for anonymous).
        action: One of VIEW/CREATE/UPDATE/DELETE/ASSIGN/EXPORT.
        resource_type: e.g. patient, medication, report, alert.
        resource_id: The ID of the affected resource (string representation).
        details: Additional context as a JSON-serializable dict.
        db: Async database session.
        ip_address: Client IP address (optional).

    Returns:
        The created OperationLog instance.
    """
    if action not in VALID_ACTIONS:
        action = "VIEW"

    op = OperationLog(
        id=uuid.uuid4(),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        timestamp=datetime.utcnow(),
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    return op


async def get_audit_logs(
    db: AsyncSession,
    *,
    user_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Query audit logs with optional filters.

    Returns paginated results: {total, page, page_size, items}.
    """
    query = select(OperationLog)

    if user_id:
        query = query.where(OperationLog.user_id == user_id)
    if action:
        query = query.where(OperationLog.action == action)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)
    if resource_id:
        query = query.where(OperationLog.resource_id == resource_id)

    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        query
        .order_by(desc(OperationLog.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        {
            "id": str(op.id),
            "user_id": str(op.user_id) if op.user_id else None,
            "action": op.action,
            "resource_type": op.resource_type,
            "resource_id": op.resource_id,
            "details": op.details,
            "ip_address": op.ip_address,
            "timestamp": op.timestamp.isoformat(),
        }
        for op in logs
    ]

    return {"total": total, "page": page, "page_size": page_size, "items": items}
