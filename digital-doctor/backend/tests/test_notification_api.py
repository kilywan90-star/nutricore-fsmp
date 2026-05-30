"""Tests for notification API endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.db.base import Base
from src.db.session import get_db
from src.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def client():
    """API test client with a fresh database."""
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


async def _register_and_login(client):
    """Helper: register a new user and return auth token."""
    phone = "notify_test_phone_hash_32chars"
    password = "notify_pass_123"
    await client.post("/api/v1/auth/register", json={
        "phone_hash": phone,
        "password": password,
    })
    login_resp = await client.post("/api/v1/auth/login", json={
        "phone_hash": phone,
        "password": password,
    })
    return login_resp.json()["access_token"]


@pytest.mark.asyncio
async def test_list_notifications(client):
    """GET /notifications should return paginated notification list."""
    token = await _register_and_login(client)

    # Create a couple of test notifications
    await client.post("/api/v1/notifications/test", json={
        "title": "Reminder 1", "body": "Body 1", "channel": "app",
    }, headers={"Authorization": f"Bearer {token}"})
    await client.post("/api/v1/notifications/test", json={
        "title": "Reminder 2", "body": "Body 2", "channel": "app",
    }, headers={"Authorization": f"Bearer {token}"})

    response = await client.get("/api/v1/notifications", headers={
        "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_mark_notification_read(client):
    """POST /notifications/{id}/read should mark notification as read."""
    token = await _register_and_login(client)

    # Create a test notification
    create_resp = await client.post("/api/v1/notifications/test", json={
        "title": "Mark Read Test", "body": "Will be marked read", "channel": "app",
    }, headers={"Authorization": f"Bearer {token}"})
    nid = create_resp.json()["id"]

    response = await client.post(f"/api/v1/notifications/{nid}/read", headers={
        "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "read"


@pytest.mark.asyncio
async def test_send_test_notification(client):
    """POST /notifications/test should create and send a test notification."""
    token = await _register_and_login(client)

    response = await client.post("/api/v1/notifications/test", json={
        "title": "My Test",
        "body": "Test body content",
        "channel": "app",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "My Test"
    assert data["body"] == "Test body content"
    assert data["status"] == "sent"
    assert "id" in data
