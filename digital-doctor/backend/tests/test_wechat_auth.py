"""Tests for WeChat login endpoint and openid association.

Covers:
- WeChat login endpoint creates a user and returns JWT tokens
- OpenID is properly stored on the User model
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from src.db.base import Base
from src.db.session import get_db
from src.main import app
import src.services.auth_service as auth_service

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
except ImportError:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker  # type: ignore


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Pre-wire a known code→openid mapping for deterministic tests
KNOWN_CODE = "test_wechat_code_123"
KNOWN_OPENID = "wx_openid_test_user_001"


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

    # Wire mock openid exchange
    auth_service._wechat_code_to_openid_override = {KNOWN_CODE: KNOWN_OPENID}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up
    auth_service._wechat_code_to_openid_override = None
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_wechat_login_creates_user_and_returns_tokens(client):
    """POST /api/v1/auth/wechat-login with a known code should create user and return JWT."""
    response = await client.post("/api/v1/auth/wechat-login", json={
        "code": KNOWN_CODE,
        "name_hash": "wechat_test_user",
        "gender": "M",
        "birth_year": 1980,
        "diabetes_type": "type2",
    })

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "patient"
    assert data["user"]["is_active"] is True

    # Second login with same code should also succeed (existing user)
    response2 = await client.post("/api/v1/auth/wechat-login", json={
        "code": KNOWN_CODE,
    })
    assert response2.status_code == 200
    assert "access_token" in response2.json()


@pytest.mark.asyncio
async def test_wechat_login_stores_openid(client):
    """After wechat login, the /me endpoint should show the user, and the User
    record has the correct wechat_openid via the auth service.
    """
    # Login
    login_resp = await client.post("/api/v1/auth/wechat-login", json={
        "code": KNOWN_CODE,
    })
    token = login_resp.json()["access_token"]

    # Verify the /me endpoint works with the wechat-issued token
    me_resp = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["role"] == "patient"

    # Verify openid association by checking that a raw DB query returns the openid
    # (We test this indirectly: the mock openid exchange should result in
    #  a lookup hit rather than a new user on the second call.)
    # Second login uses same code — should find existing user, not fail
    resp2 = await client.post("/api/v1/auth/wechat-login", json={
        "code": KNOWN_CODE,
    })
    assert resp2.status_code == 200
    # The same user ID should be returned
    assert resp2.json()["user"]["id"] == login_resp.json()["user"]["id"]


@pytest.mark.asyncio
async def test_wechat_login_invalid_code(client):
    """A code not in the mock mapping should return 401."""
    response = await client.post("/api/v1/auth/wechat-login", json={
        "code": "nonexistent_code",
    })
    assert response.status_code == 401
