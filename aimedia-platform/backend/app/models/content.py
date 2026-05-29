import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import GUID, JSONType


class Content(Base):
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    hospital_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hospitals.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default="article")
    body: Mapped[dict] = mapped_column(JSONType, default=dict)
    cover_url: Mapped[Optional[str]] = mapped_column(String(500))
    ai_generated: Mapped[bool] = mapped_column(default=False)
    ai_generated_parts: Mapped[Optional[dict]] = mapped_column(JSONType)
    medical_tags: Mapped[Optional[list]] = mapped_column(JSONType)
    source_references: Mapped[Optional[list]] = mapped_column(JSONType)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
