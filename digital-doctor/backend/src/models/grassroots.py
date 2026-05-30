"""Grassroots screening & follow-up models for community health deployment."""

import uuid
import enum
from datetime import date, datetime

from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, Text, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ReferralStatus(str, enum.Enum):
    NONE = "none"
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"


class GrassrootsPatient(Base):
    """Lightweight patient record for community health workers."""

    __tablename__ = "grassroots_patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    village: Mapped[str] = mapped_column(String(200))
    gender: Mapped[str] = mapped_column(String(1))
    birth_year: Mapped[int] = mapped_column(Integer)
    diabetes_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    screenings: Mapped[list["GrassrootsScreening"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    follow_ups: Mapped[list["GrassrootsFollowUp"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class GrassrootsScreening(Base):
    """Community screening record — minimal 6-field input."""

    __tablename__ = "grassroots_screenings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grassroots_patients.id"), index=True
    )
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(1))
    waist_circumference: Mapped[float] = mapped_column(Float)
    fasting_glucose: Mapped[float] = mapped_column(Float)
    systolic_bp: Mapped[int] = mapped_column(Integer)
    diastolic_bp: Mapped[int] = mapped_column(Integer)
    family_history: Mapped[bool] = mapped_column(Boolean)
    risk_level: Mapped[RiskLevel] = mapped_column(SAEnum(RiskLevel))
    risk_score: Mapped[int] = mapped_column(Integer)
    referral_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_status: Mapped[ReferralStatus] = mapped_column(SAEnum(ReferralStatus), default=ReferralStatus.NONE)
    referral_hospital: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    screened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    synced: Mapped[bool] = mapped_column(Boolean, default=False)

    patient: Mapped["GrassrootsPatient"] = relationship(back_populates="screenings")


class GrassrootsFollowUp(Base):
    """Follow-up visit record for managed patients."""

    __tablename__ = "grassroots_follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grassroots_patients.id"), index=True
    )
    glucose_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    medication_adherent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    new_symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    referral_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    followed_up_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    next_follow_up: Mapped[date | None] = mapped_column(Date, nullable=True)
    synced: Mapped[bool] = mapped_column(Boolean, default=False)

    patient: Mapped["GrassrootsPatient"] = relationship(back_populates="follow_ups")
