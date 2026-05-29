"""审核管理 API"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.engine.review.workflow import ReviewWorkflowEngine
from app.models.content import Content
from app.models.review import ReviewRecord
from app.models.user import User

router = APIRouter(prefix="/api/review", tags=["review"])


class ReviewSubmit(BaseModel):
    content_id: str
    action: str = Field(description="approve / reject / return")
    comment: str = ""
    review_level: int = Field(ge=1, le=5)


class ReviewResponse(BaseModel):
    content_id: str
    new_status: str
    action: str


@router.post("/submit", response_model=ReviewResponse)
async def submit_review(data: ReviewSubmit, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    content_id = UUID(data.content_id)
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    engine = ReviewWorkflowEngine()
    new_status = engine.next_status(content.status, data.action)

    record = ReviewRecord(
        id=uuid4(),
        content_id=content_id,
        review_level=data.review_level,
        reviewer_id=current_user.id,
        action=data.action,
        comment=data.comment,
    )
    db.add(record)
    content.status = new_status
    await db.commit()

    return ReviewResponse(
        content_id=str(content_id),
        new_status=new_status,
        action=data.action,
    )


@router.get("/records/{content_id}")
async def get_review_records(content_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReviewRecord)
        .where(ReviewRecord.content_id == content_id)
        .order_by(ReviewRecord.reviewed_at.desc())
    )
    records = result.scalars().all()
    return {
        "records": [
            {"id": str(r.id), "review_level": r.review_level,
             "action": r.action, "comment": r.comment,
             "reviewed_at": r.reviewed_at.isoformat()}
            for r in records
        ]
    }
