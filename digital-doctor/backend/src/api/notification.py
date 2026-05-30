"""Push notification API endpoints."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.notification import Notification, NotificationStatus, NotificationType, NotificationChannel
from src.models.user import User
from src.api.auth_deps import get_current_user

router = APIRouter()


class NotificationResponse(BaseModel):
    id: str
    notification_type: str
    title: str
    body: str
    channel: str
    scheduled_at: str
    sent_at: str | None
    status: str
    metadata: dict | None


class NotificationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NotificationResponse]


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's notifications, paginated and optionally filtered by status."""
    query = select(Notification).where(Notification.user_id == user.id)

    if status:
        try:
            ns = NotificationStatus(status)
            query = query.where(Notification.status == ns)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(desc(Notification.scheduled_at)).offset(
        (page - 1) * page_size
    ).limit(page_size)

    result = await db.execute(query)
    notifications = result.scalars().all()

    items = [
        NotificationResponse(
            id=str(n.id),
            notification_type=n.notification_type.value,
            title=n.title,
            body=n.body,
            channel=n.channel.value,
            scheduled_at=n.scheduled_at.isoformat(),
            sent_at=n.sent_at.isoformat() if n.sent_at else None,
            status=n.status.value,
            metadata=n.metadata_,
        )
        for n in notifications
    ]

    return NotificationListResponse(total=total, page=page, page_size=page_size, items=items)


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    try:
        nid = uuid.UUID(notification_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    stmt = select(Notification).where(
        Notification.id == nid,
        Notification.user_id == user.id,
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = NotificationStatus.READ
    await db.commit()

    return {"id": str(notification.id), "status": "read"}


class TestNotificationRequest(BaseModel):
    title: str = Field(default="Test Notification")
    body: str = Field(default="This is a test notification from the API.")
    channel: str = Field(default="app", pattern="^(wechat|sms|app)$")


@router.post("/notifications/test")
async def send_test_notification(
    req: TestNotificationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test notification to the current user (dev only)."""
    notification = Notification(
        user_id=user.id,
        notification_type=NotificationType.HEALTH_TIP,
        title=req.title,
        body=req.body,
        channel=NotificationChannel(req.channel),
        scheduled_at=datetime.utcnow(),
        status=NotificationStatus.SENT,
        sent_at=datetime.utcnow(),
    )
    db.add(notification)
    await db.commit()

    return {
        "id": str(notification.id),
        "title": notification.title,
        "body": notification.body,
        "channel": notification.channel.value,
        "status": notification.status.value,
    }
