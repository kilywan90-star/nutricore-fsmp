import uuid
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from src.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name_hash: Mapped[str] = mapped_column(String(128), index=True)
    gender: Mapped[str] = mapped_column(String(1))
    birth_year: Mapped[int] = mapped_column(Integer)
    diabetes_type: Mapped[str] = mapped_column(String(20))
    diagnosis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    hba1c_target: Mapped[float] = mapped_column(Float, default=7.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    glucose_records: Mapped[list["GlucoseRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    medications: Mapped[list["MedicationReminder"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    lab_reports: Mapped[list["LabReport"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    medical_records: Mapped[list["MedicalRecord"]] = relationship(back_populates="patient", cascade="all, delete-orphan")


class GlucoseRecord(Base):
    __tablename__ = "glucose_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    value_mmol_l: Mapped[float] = mapped_column(Float)
    measure_type: Mapped[str] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="glucose_records")


class MedicationReminder(Base):
    __tablename__ = "medication_reminders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    drug_name: Mapped[str] = mapped_column(String(100))
    dosage: Mapped[str] = mapped_column(String(50))
    frequency: Mapped[str] = mapped_column(String(20))
    time_of_day: Mapped[list[str]] = mapped_column(JSON)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    patient: Mapped["Patient"] = relationship(back_populates="medications")
