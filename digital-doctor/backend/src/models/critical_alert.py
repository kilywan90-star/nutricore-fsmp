"""Critical alert model for 3-tier closed-loop system."""
import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base


class CriticalAlertStatus(str, enum.Enum):
    DETECTED = "detected"
    NOTIFIED_DOCTOR = "notified_doctor"
    DOCTOR_ACKNOWLEDGED = "doctor_acknowledged"
    NURSE_CONFIRMED = "nurse_confirmed"       # standard mode only
    PATIENT_NOTIFIED = "patient_notified"      # complete mode only
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    EXPIRED = "expired"  # timeout without ack


class CriticalAlert(Base):
    __tablename__ = "critical_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(50))  # severe_hyperglycemia, hypoglycemia
    severity: Mapped[str] = mapped_column(String(20), default="critical")
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(String(500))
    value: Mapped[float] = mapped_column(Float)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    doctor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True)
    status: Mapped[CriticalAlertStatus] = mapped_column(
        SAEnum(CriticalAlertStatus), default=CriticalAlertStatus.DETECTED, index=True
    )
    status_history: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    escalated_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 已处理/已联系患者/转急诊
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="critical_alerts")
