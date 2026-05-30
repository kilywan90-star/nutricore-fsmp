"""Integration tests for doctor permissions — scoped patient listing and visibility."""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.db.base import Base
from src.db.session import get_db
from src.main import app
from src.models.user import User, UserRole
from src.models.org import Department, DoctorProfile, PatientAssignment, AssignmentType
from src.models.patient import Patient
from src.security.jwt import create_access_token

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def permissions_client():
    """Client with pre-seeded department, doctors, and patient assignments."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    # ── Seed test data ─────────────────────────────────────────────────────
    async with async_session() as session:
        # Department
        dept_endo = Department(id=uuid.uuid4(), name="内分泌科", code="endocrinology", is_active=True)
        dept_cardio = Department(id=uuid.uuid4(), name="心内科", code="cardiology", is_active=True)
        session.add_all([dept_endo, dept_cardio])
        await session.flush()

        # Doctor 1 (内分泌科, regular)
        doctor_user = User(
            id=uuid.uuid4(),
            phone_hash="phone_endo_doc",
            password_hash="hashed",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        session.add(doctor_user)
        await session.flush()
        doctor_profile = DoctorProfile(
            id=uuid.uuid4(),
            user_id=doctor_user.id,
            department_id=dept_endo.id,
            title="主治医师",
            is_active=True,
            is_department_head=False,
        )
        session.add(doctor_profile)
        await session.flush()

        # Department Head (内分泌科)
        head_user = User(
            id=uuid.uuid4(),
            phone_hash="phone_endo_head",
            password_hash="hashed",
            role=UserRole.DEPARTMENT_HEAD,
            is_active=True,
        )
        session.add(head_user)
        await session.flush()
        head_profile = DoctorProfile(
            id=uuid.uuid4(),
            user_id=head_user.id,
            department_id=dept_endo.id,
            title="主任医师",
            is_active=True,
            is_department_head=True,
        )
        session.add(head_profile)
        await session.flush()

        # Doctor 2 (心内科)
        cardio_user = User(
            id=uuid.uuid4(),
            phone_hash="phone_cardio_doc",
            password_hash="hashed",
            role=UserRole.DOCTOR,
            is_active=True,
        )
        session.add(cardio_user)
        await session.flush()
        cardio_profile = DoctorProfile(
            id=uuid.uuid4(),
            user_id=cardio_user.id,
            department_id=dept_cardio.id,
            title="副主任医师",
            is_active=True,
            is_department_head=False,
        )
        session.add(cardio_profile)
        await session.flush()

        # Admin
        admin_user = User(
            id=uuid.uuid4(),
            phone_hash="phone_admin",
            password_hash="hashed",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin_user)
        await session.flush()

        # Patients
        p1 = Patient(id=uuid.uuid4(), name_hash="patient_one", gender="M", birth_year=1970, diabetes_type="type2")
        p2 = Patient(id=uuid.uuid4(), name_hash="patient_two", gender="F", birth_year=1980, diabetes_type="type2")
        p3 = Patient(id=uuid.uuid4(), name_hash="patient_three", gender="M", birth_year=1965, diabetes_type="type2")
        p4 = Patient(id=uuid.uuid4(), name_hash="patient_four", gender="F", birth_year=1975, diabetes_type="type2")
        session.add_all([p1, p2, p3, p4])
        await session.flush()

        # Assignments: Doctor (内分泌科) gets p1, p2; Cardio doc gets p3; Head has p1
        session.add_all([
            PatientAssignment(patient_id=p1.id, doctor_id=doctor_profile.id, assignment_type=AssignmentType.PRIMARY, is_active=True),
            PatientAssignment(patient_id=p2.id, doctor_id=doctor_profile.id, assignment_type=AssignmentType.PRIMARY, is_active=True),
            PatientAssignment(patient_id=p3.id, doctor_id=cardio_profile.id, assignment_type=AssignmentType.PRIMARY, is_active=True),
            PatientAssignment(patient_id=p1.id, doctor_id=head_profile.id, assignment_type=AssignmentType.CONSULTING, is_active=True),
        ])
        await session.commit()

        test_ids = {
            "doctor_user_id": str(doctor_user.id),
            "head_user_id": str(head_user.id),
            "cardio_user_id": str(cardio_user.id),
            "admin_user_id": str(admin_user.id),
            "doctor_profile_id": str(doctor_profile.id),
            "head_profile_id": str(head_profile.id),
            "p1_id": str(p1.id),
            "p2_id": str(p2.id),
            "p3_id": str(p3.id),
            "p4_id": str(p4.id),
        }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, test_ids

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _auth_header(user_id: str, role: str) -> dict:
    token = create_access_token(user_id, role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_doctor_sees_only_assigned_patients(permissions_client):
    client, ids = permissions_client

    headers = _auth_header(ids["doctor_user_id"], "doctor")
    response = await client.get("/api/v1/doctor/my-patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    patient_names = {item["gender"] for item in data["items"]}
    # Doctor has p1(M) and p2(F) — should see both
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_dept_head_sees_all_department_patients(permissions_client):
    client, ids = permissions_client

    headers = _auth_header(ids["head_user_id"], "department_head")
    response = await client.get("/api/v1/doctor/department/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # Head is in 内分泌科 which has p1, p2, and dept head's own assignment to p1
    # get_department_patient_ids returns all patients for ALL doctors in the dept
    # Doctor in endo has p1, p2; head also has p1 → unique patients: p1, p2
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_admin_sees_all_patients(permissions_client):
    client, ids = permissions_client

    headers = _auth_header(ids["admin_user_id"], "admin")
    response = await client.get("/api/v1/doctor/patients", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # Admin should see all 4 patients
    assert data["total"] == 4


@pytest.mark.asyncio
async def test_assign_patient_to_doctor(permissions_client):
    client, ids = permissions_client

    headers = _auth_header(ids["doctor_user_id"], "doctor")
    response = await client.post(
        f"/api/v1/doctor/patients/{ids['p4_id']}/assign",
        json={"assignment_type": "primary"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == ids["p4_id"]
    assert data["assignment_type"] == "primary"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_doctor_profile_endpoint(permissions_client):
    client, ids = permissions_client

    headers = _auth_header(ids["doctor_user_id"], "doctor")
    response = await client.get("/api/v1/doctor/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["department_code"] == "endocrinology"
    assert "patient_count" in data
