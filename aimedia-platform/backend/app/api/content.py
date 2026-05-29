"""内容管理 API"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.engine.compliance import ComplianceEngine
from app.engine.review.workflow import ContentStatus
from app.models.content import Content
from app.models.user import User

router = APIRouter(prefix="/api/content", tags=["content"])


class ContentCreate(BaseModel):
    title: str = Field(max_length=200)
    content_type: str = "article"
    body: dict = Field(default_factory=dict)
    medical_tags: list[str] = Field(default_factory=list)
    source_references: list[str] = Field(default_factory=list)
    ai_generated: bool = False


class ContentResponse(BaseModel):
    id: str
    title: str
    content_type: str
    status: str
    ai_generated: bool
    created_at: str


@router.post("", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_content(data: ContentCreate, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    content = Content(
        id=uuid4(),
        hospital_id=current_user.hospital_id,
        title=data.title,
        content_type=data.content_type,
        body=data.body,
        medical_tags=data.medical_tags,
        source_references=data.source_references,
        ai_generated=data.ai_generated,
        status=ContentStatus.DRAFT.value,
        created_by=current_user.id,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)

    return ContentResponse(
        id=str(content.id), title=content.title,
        content_type=content.content_type, status=content.status,
        ai_generated=content.ai_generated,
        created_at=content.created_at.isoformat() if content.created_at else "",
    )


@router.get("/{content_id}")
async def get_content(content_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    return {
        "id": str(content.id), "title": content.title,
        "content_type": content.content_type, "body": content.body,
        "status": content.status, "ai_generated": content.ai_generated,
        "medical_tags": content.medical_tags,
        "source_references": content.source_references,
    }


@router.post("/{content_id}/submit")
async def submit_for_review(content_id: UUID, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    """提交草稿进入审核流程"""
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")
    if content.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿状态可以提交审核")

    from app.engine.review.workflow import ReviewWorkflowEngine
    engine = ReviewWorkflowEngine()
    new_status = engine.next_status(content.status, "submit")
    content.status = new_status
    await db.commit()
    return {"content_id": str(content_id), "status": new_status}


@router.get("")
async def list_contents(status: str = None, limit: int = 20, offset: int = 0,
                        db: AsyncSession = Depends(get_db)):
    query = select(Content)
    if status:
        query = query.where(Content.status == status)
    query = query.order_by(Content.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    contents = result.scalars().all()
    return {
        "items": [{"id": str(c.id), "title": c.title, "status": c.status,
                    "content_type": c.content_type, "created_at": c.created_at.isoformat()}
                  for c in contents],
        "total": len(contents),
    }


@router.post("/{content_id}/compliance-check")
async def compliance_check(content_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="内容不存在")

    engine = ComplianceEngine()
    report = await engine.scan(
        {"title": content.title, "body": content.body},
        content_type=content.content_type,
        is_ai_generated=content.ai_generated,
    )

    from app.models.review import ComplianceLog
    log = ComplianceLog(
        id=uuid4(), content_id=content.id,
        content_snapshot_hash=report.content_hash,
        rule_results={"findings": [f.__dict__ for f in report.rule_findings]},
        privacy_findings=[f.__dict__ for f in report.privacy_findings],
        overall_verdict=report.overall_verdict.value,
    )
    db.add(log)
    await db.commit()

    return report.to_dict()
