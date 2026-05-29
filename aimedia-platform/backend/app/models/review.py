import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import GUID, JSONType


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.id"), nullable=False)
    review_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text)
    compliance_report: Mapped[Optional[dict]] = mapped_column(JSONType)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sla_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)


class ComplianceLog(Base):
    __tablename__ = "compliance_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contents.id"), nullable=False)
    content_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_results: Mapped[dict] = mapped_column(JSONType, default=dict)
    llm_results: Mapped[Optional[dict]] = mapped_column(JSONType)
    privacy_findings: Mapped[list] = mapped_column(JSONType, default=list)
    overall_verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
