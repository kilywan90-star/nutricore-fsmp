import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from src.db.base import Base


class AssignmentType(str, enum.Enum):
    PRIMARY = "primary"
    CONSULTING = "consulting"


class HospitalLevel(str, enum.Enum):
    III_A = "三级甲等"
    III_B = "三级乙等"
    II_A = "二级甲等"
    II_B = "二级乙等"
    I_A = "一级甲等"


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    level: Mapped[HospitalLevel | None] = mapped_column(SAEnum(HospitalLevel), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    departments: Mapped[list["Department"]] = relationship(back_populates="hospital", cascade="save-update")
    doctors: Mapped[list["DoctorProfile"]] = relationship(back_populates="hospital", cascade="save-update")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    hospital: Mapped["Hospital | None"] = relationship(back_populates="departments")
    doctors: Mapped[list["DoctorProfile"]] = relationship(back_populates="department", cascade="save-update")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)
    department_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"), index=True)
    hospital_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(50))
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_department_head: Mapped[bool] = mapped_column(Boolean, default=False)

    department: Mapped["Department"] = relationship(back_populates="doctors")
    hospital: Mapped["Hospital | None"] = relationship(back_populates="doctors")
    patient_assignments: Mapped[list["PatientAssignment"]] = relationship(back_populates="doctor", cascade="all, delete-orphan")


class PatientAssignment(Base):
    __tablename__ = "patient_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("doctor_profiles.id"), index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assignment_type: Mapped[AssignmentType] = mapped_column(SAEnum(AssignmentType), default=AssignmentType.PRIMARY)

    doctor: Mapped["DoctorProfile"] = relationship(back_populates="patient_assignments")


class TransferStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class TransferRecord(Base):
    __tablename__ = "transfer_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    from_hospital_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hospitals.id"))
    to_hospital_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hospitals.id"))
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status: Mapped[TransferStatus] = mapped_column(SAEnum(TransferStatus), default=TransferStatus.PENDING)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(20))
    resource_type: Mapped[str] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
