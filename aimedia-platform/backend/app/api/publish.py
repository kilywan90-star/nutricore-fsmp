"""发布管理 API"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.engine.publish import PublishScheduler
from app.models.content import Content
from app.models.publish import PublishTask, PublishRecord

router = APIRouter(prefix="/api/publish", tags=["publish"])


class PublishRequest(BaseModel):
    content_id: str
    channels: list[str]
    schedule_type: str = "immediate"  # immediate / scheduled
    scheduled_at: str | None = None


@router.post("/submit")
async def submit_publish(data: PublishRequest, db: AsyncSession = Depends(get_db)):
    """提交发布任务"""
    content_id = UUID(data.content_id)

    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    if content.status != "approved":
        raise HTTPException(status_code=400, detail="只有已审核通过的内容才能发布")

    # 创建发布任务
    task = PublishTask(
        id=uuid4(), content_id=content_id,
        channels=data.channels,
        schedule_type=data.schedule_type,
        scheduled_at=data.scheduled_at,
        status="pending",
    )
    db.add(task)

    # 更新内容状态
    content.status = "published"

    await db.commit()
    await db.refresh(task)

    return {"task_id": str(task.id), "status": task.status}


@router.get("/tasks")
async def list_publish_tasks(limit: int = 20, offset: int = 0,
                             db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PublishTask).order_by(PublishTask.created_at.desc()).offset(offset).limit(limit)
    )
    tasks = result.scalars().all()
    return {
        "items": [{"id": str(t.id), "content_id": str(t.content_id),
                    "channels": t.channels, "status": t.status,
                    "created_at": t.created_at.isoformat()}
                  for t in tasks],
    }


@router.post("/{task_id}/retract")
async def retract_publish(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """撤回发布"""
    result = await db.execute(select(PublishTask).where(PublishTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="发布任务不存在")

    scheduler = PublishScheduler()
    retract_result = await scheduler.retract(task.content_id, task.channels)

    task.status = "retracted"
    await db.commit()

    return {"task_id": str(task_id), "retract_results": retract_result}
