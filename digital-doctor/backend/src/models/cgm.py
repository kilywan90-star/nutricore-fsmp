import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base


class CGMDevice(str, enum.Enum):
    FREESTYLE_LIBRE = "freestyle_libre"
    DEXCOM_G6 = "dexcom_g6"
    DEXCOM_G7 = "dexcom_g7"
    MEDTRONIC_GUARDIAN = "medtronic"
    SINOCARE = "sinocare"
    MICROTECH = "microtech"
    UNKNOWN = "unknown"


class CGMRecord(Base):
    __tablename__ = "cgm_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cgm_sessions.id"), index=True)
    device_type: Mapped[CGMDevice] = mapped_column(SAEnum(CGMDevice))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    value_mmol_l: Mapped[float] = mapped_column(Float)
    trend_direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_manual_calibration: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="cgm_records")
    session: Mapped["CGMSession"] = relationship(back_populates="records")


class CGMSession(Base):
    __tablename__ = "cgm_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    device_type: Mapped[CGMDevice] = mapped_column(SAEnum(CGMDevice))
    sensor_start: Mapped[datetime] = mapped_column(DateTime)
    sensor_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_readings: Mapped[int] = mapped_column(Integer, default=0)
    avg_glucose: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_hba1c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cv_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_in_range_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_above_range_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_below_range_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_in_tight_range_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mage: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["Patient"] = relationship(back_populates="cgm_sessions")
    records: Mapped[list["CGMRecord"]] = relationship(back_populates="session", cascade="all, delete-orphan")
