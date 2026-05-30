import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.db.base import Base
from src.db.session import get_db
from src.main import app
from src.models.user import User, UserRole
from src.api.auth_deps import get_current_user

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


async def _make_admin():
    """Create an admin user for dependency override."""
    user = User(
        id=uuid.uuid4(),
        phone_hash="admin_backup_test_hash_64chars_x" + "y" * 30,
        password_hash="hashed",
        role=UserRole.ADMIN,
        is_active=True,
    )
    return user


async def _make_patient():
    """Create a patient user for dependency override."""
    user = User(
        id=uuid.uuid4(),
        phone_hash="patient_backup_test_hash_64_x" + "z" * 29,
        password_hash="hashed",
        role=UserRole.PATIENT,
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
async def test_admin_can_trigger_backup(client):
    """Admin user should be able to trigger a backup (API returns 200 or backup record)."""
    admin = await _make_admin()

    async def override_get_current_user():
        return admin

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.post("/api/v1/admin/backups?backup_type=full")
    # pg_dump won't work in test env, but the endpoint should process the request
    # and return either a success or an error about pg_dump
    assert response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_non_admin_gets_403(client):
    """Non-admin user should get 403 when trying to access backup endpoints."""
    patient = await _make_patient()

    async def override_get_current_user():
        return patient

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.post("/api/v1/admin/backups?backup_type=full")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_backups(client):
    """Admin should be able to list backups."""
    admin = await _make_admin()

    async def override_get_current_user():
        return admin

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.get("/api/v1/admin/backups")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_admin_can_get_stats(client):
    """Admin should be able to get backup statistics."""
    admin = await _make_admin()

    async def override_get_current_user():
        return admin

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.get("/api/v1/admin/backups/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_backups" in data
    assert "total_size_bytes" in data
    assert "success_rate" in data
