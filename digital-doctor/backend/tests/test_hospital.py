"""Tests for hospital management, scoped queries, and transfer workflows."""

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select as sa_select

from src.db.base import Base
from src.db.session import get_db
from src.main import app
from src.models.user import User, UserRole
from src.models.org import Hospital, HospitalLevel, Department, DoctorProfile, TransferRecord, TransferStatus
from src.models.patient import Patient
from src.api.auth_deps import get_current_user

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _make_admin():
    return User(
        id=uuid.uuid4(),
        phone_hash="admin_hosp_test_" + "x" * 46,
        password_hash="hashed",
        role=UserRole.ADMIN,
        is_active=True,
    )


async def _make_doctor(hospital_id: uuid.UUID = None, dept_id: uuid.UUID = None):
    user = User(
        id=uuid.uuid4(),
        phone_hash="doc_hosp_test_" + uuid.uuid4().hex[:20],
        password_hash="hashed",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    return user


@pytest_asyncio.fixture
async def client():
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_hospital_crud(client):
    """Test creating, listing, and updating hospitals (admin only)."""
    admin = await _make_admin()

    # Get DB session to seed admin user
    async for session in app.dependency_overrides[get_db]():
        session.add(admin)
        await session.commit()
        break

    async def override_get_current_user():
        return admin

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create hospital
    resp = await client.post("/api/v1/admin/hospitals", json={
        "name": "Test General Hospital",
        "code": "TGH001",
        "address": "123 Test Street",
        "level": "三级甲等",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test General Hospital"
    assert data["code"] == "TGH001"
    assert data["level"] == "三级甲等"
    hosp_id = data["id"]

    # Duplicate code should fail
    resp2 = await client.post("/api/v1/admin/hospitals", json={
        "name": "Duplicate",
        "code": "TGH001",
    })
    assert resp2.status_code == 400

    # List hospitals
    resp3 = await client.get("/api/v1/admin/hospitals")
    assert resp3.status_code == 200
    list_data = resp3.json()
    assert list_data["total"] >= 1

    # Update hospital
    resp4 = await client.put(f"/api/v1/admin/hospitals/{hosp_id}", json={
        "name": "Updated Hospital",
    })
    assert resp4.status_code == 200
    assert resp4.json()["name"] == "Updated Hospital"

    # Clean up override
    del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_hospital_scoped_query(client):
    """Test that hospital stats endpoint correctly scopes data by hospital."""
    admin = await _make_admin()

    async for session in app.dependency_overrides[get_db]():
        session.add(admin)

        h1 = Hospital(name="Hospital A", code="HA", is_active=True)
        h2 = Hospital(name="Hospital B", code="HB", is_active=True)
        session.add_all([h1, h2])
        await session.commit()
        await session.refresh(h1)
        await session.refresh(h2)

        d1 = Department(name="Dept A", code="DA", hospital_id=h1.id, is_active=True)
        d2 = Department(name="Dept B", code="DB", hospital_id=h2.id, is_active=True)
        session.add_all([d1, d2])
        await session.commit()
        await session.refresh(d1)
        await session.refresh(d2)

        # Create a doctor in Hospital A
        doc_user = await _make_doctor()
        session.add(doc_user)
        await session.commit()

        profile = DoctorProfile(
            user_id=doc_user.id,
            department_id=d1.id,
            hospital_id=h1.id,
            title="主治医师",
            is_active=True,
        )
        session.add(profile)
        await session.commit()
        break

    async def override_get_current_user():
        return admin

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Get stats for Hospital A
    resp = await client.get(f"/api/v1/admin/hospitals/{h1.id}/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["hospital_name"] == "Hospital A"
    assert stats["department_count"] == 1
    assert stats["doctor_count"] == 1

    # Get stats for Hospital B (no doctors)
    resp2 = await client.get(f"/api/v1/admin/hospitals/{h2.id}/stats")
    assert resp2.status_code == 200
    stats2 = resp2.json()
    assert stats2["hospital_name"] == "Hospital B"
    assert stats2["doctor_count"] == 0

    del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_transfer_initiation(client):
    """Test patient transfer request creation, same-hospital validation, and approval."""
    admin = await _make_admin()

    async for session in app.dependency_overrides[get_db]():
        session.add(admin)

        h1 = Hospital(name="Source Hospital", code="SH", is_active=True)
        h2 = Hospital(name="Target Hospital", code="TH", is_active=True)
        session.add_all([h1, h2])
        await session.commit()
        await session.refresh(h1)
        await session.refresh(h2)

        patient = Patient(
            name_hash="test_transfer_patient_" + "x" * 20,
            gender="M",
            birth_year=1980,
            diabetes_type="type2",
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)

        break

    async def override_get_current_user():
        return admin

    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create transfer
    resp = await client.post("/api/v1/admin/transfers", json={
        "patient_id": str(patient.id),
        "from_hospital_id": str(h1.id),
        "to_hospital_id": str(h2.id),
        "reason": "Specialized endocrinology care required",
    })
    assert resp.status_code == 200
    transfer_data = resp.json()
    assert transfer_data["status"] == "pending"
    assert transfer_data["from_hospital_name"] == "Source Hospital"
    assert transfer_data["to_hospital_name"] == "Target Hospital"
    transfer_id = transfer_data["id"]

    # Same-hospital transfer should fail
    resp2 = await client.post("/api/v1/admin/transfers", json={
        "patient_id": str(patient.id),
        "from_hospital_id": str(h1.id),
        "to_hospital_id": str(h1.id),
    })
    assert resp2.status_code == 400

    # Approve transfer
    resp3 = await client.post(f"/api/v1/admin/transfers/{transfer_id}/approve", json={
        "approved": True,
    })
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "approved"

    # List transfers
    resp4 = await client.get("/api/v1/admin/transfers")
    assert resp4.status_code == 200
    transfer_list = resp4.json()
    assert transfer_list["total"] >= 1

    # Reject a second transfer
    resp5 = await client.post("/api/v1/admin/transfers", json={
        "patient_id": str(patient.id),
        "from_hospital_id": str(h2.id),
        "to_hospital_id": str(h1.id),
        "reason": "Return transfer",
    })
    assert resp5.status_code == 200
    transfer2_id = resp5.json()["id"]

    resp6 = await client.post(f"/api/v1/admin/transfers/{transfer2_id}/approve", json={
        "approved": False,
    })
    assert resp6.status_code == 200
    assert resp6.json()["status"] == "rejected"

    del app.dependency_overrides[get_current_user]
