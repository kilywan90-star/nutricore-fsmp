"""Medical record models — SOAP notes, discharge summaries, progress notes."""
import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base


class RecordType(str, enum.Enum):
    SOAP = "soap"
    DISCHARGE = "discharge"
    PROGRESS = "progress"


class RecordStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    record_type: Mapped[RecordType] = mapped_column(SAEnum(RecordType))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    markdown: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[RecordStatus] = mapped_column(SAEnum(RecordStatus), default=RecordStatus.DRAFT)
    version: Mapped[int] = mapped_column(Integer, default=1)
    versions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
