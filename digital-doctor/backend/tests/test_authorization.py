"""Tests for enhanced RBAC authorization — patient access, department restriction, admin bypass, dept head scope."""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from src.db.base import Base
from src.db.session import get_db
from src.main import app
from src.models.user import User, UserRole
from src.models.org import Department, DoctorProfile, PatientAssignment, AssignmentType
from src.models.patient import Patient
from src.security.jwt import create_access_token
from src.security.authorization import can_access_patient, is_department_head

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _make_user(email_suffix: str, role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        phone_hash=f"phone_{email_suffix}",
        password_hash="hashed",
        role=role,
        is_active=True,
    )


def _make_department(name: str, code: str) -> Department:
    return Department(
        id=uuid.uuid4(),
        name=name,
        code=code,
        is_active=True,
    )


def _make_doctor_profile(user_id: uuid.UUID, department_id: uuid.UUID, title: str, is_head: bool = False) -> DoctorProfile:
    return DoctorProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        department_id=department_id,
        title=title,
        license_number=f"LIC-{user_id}"[:20],
        is_active=True,
        is_department_head=is_head,
    )


def _make_patient(name_suffix: str) -> Patient:
    return Patient(
        id=uuid.uuid4(),
        name_hash=f"name_{name_suffix}"[:32],
        gender="M",
        birth_year=1970,
        diabetes_type="type2",
    )


class TestCanAccessPatient:
    @pytest.mark.asyncio
    async def test_doctor_can_access_assigned_patient(self, db_session):
        dept = _make_department("内分泌科", "endocrinology")
        db_session.add(dept)
        await db_session.flush()

        user = _make_user("doc1", UserRole.DOCTOR)
        db_session.add(user)
        await db_session.flush()

        doctor = _make_doctor_profile(user.id, dept.id, "主治医师")
        db_session.add(doctor)
        await db_session.flush()

        patient = _make_patient("p1")
        db_session.add(patient)
        await db_session.flush()

        assignment = PatientAssignment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            assignment_type=AssignmentType.PRIMARY,
            is_active=True,
        )
        db_session.add(assignment)
        await db_session.commit()

        result = await can_access_patient(doctor.id, patient.id, db_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_doctor_cannot_access_unassigned_patient(self, db_session):
        dept = _make_department("内分泌科", "endocrinology")
        db_session.add(dept)
        await db_session.flush()

        user = _make_user("doc2", UserRole.DOCTOR)
        db_session.add(user)
        await db_session.flush()

        doctor = _make_doctor_profile(user.id, dept.id, "主治医师")
        db_session.add(doctor)
        await db_session.flush()

        patient = _make_patient("p2")
        db_session.add(patient)
        await db_session.commit()

        result = await can_access_patient(doctor.id, patient.id, db_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_inactive_assignment_denies_access(self, db_session):
        dept = _make_department("内分泌科", "endocrinology")
        db_session.add(dept)
        await db_session.flush()

        user = _make_user("doc3", UserRole.DOCTOR)
        db_session.add(user)
        await db_session.flush()

        doctor = _make_doctor_profile(user.id, dept.id, "主治医师")
        db_session.add(doctor)
        await db_session.flush()

        patient = _make_patient("p3")
        db_session.add(patient)
        await db_session.flush()

        assignment = PatientAssignment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            assignment_type=AssignmentType.PRIMARY,
            is_active=False,
        )
        db_session.add(assignment)
        await db_session.commit()

        result = await can_access_patient(doctor.id, patient.id, db_session)
        assert result is False


class TestIsDepartmentHead:
    @pytest.mark.asyncio
    async def test_admin_is_always_dept_head(self, db_session):
        user = _make_user("admin1", UserRole.ADMIN)
        db_session.add(user)
        await db_session.commit()

        result = await is_department_head(user, db_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_dept_head_flag_user(self, db_session):
        dept = _make_department("心内科", "cardiology")
        db_session.add(dept)
        await db_session.flush()

        user = _make_user("head1", UserRole.DEPARTMENT_HEAD)
        db_session.add(user)
        await db_session.flush()

        doctor = _make_doctor_profile(user.id, dept.id, "主任医师", is_head=True)
        db_session.add(doctor)
        await db_session.commit()

        result = await is_department_head(user, db_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_regular_doctor_is_not_dept_head(self, db_session):
        dept = _make_department("内分泌科", "endocrinology")
        db_session.add(dept)
        await db_session.flush()

        user = _make_user("doc4", UserRole.DOCTOR)
        db_session.add(user)
        await db_session.flush()

        doctor = _make_doctor_profile(user.id, dept.id, "主治医师", is_head=False)
        db_session.add(doctor)
        await db_session.commit()

        result = await is_department_head(user, db_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_patient_is_not_dept_head(self, db_session):
        user = _make_user("pat1", UserRole.PATIENT)
        db_session.add(user)
        await db_session.commit()

        result = await is_department_head(user, db_session)
        assert result is False
