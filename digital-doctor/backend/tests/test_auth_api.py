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
async def test_register_endpoint(client):
    response = await client.post("/api/v1/auth/register", json={
        "phone_hash": "d1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
        "password": "api_test_123",
        "name_hash": "api_user",
        "gender": "F",
        "birth_year": 1990,
        "diabetes_type": "type2",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "patient"
    assert data["message"] == "Registration successful"
    assert "id" in data


@pytest.mark.asyncio
async def test_login_endpoint(client):
    phone = "e1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    password = "api_login_123"
    await client.post("/api/v1/auth/register", json={
        "phone_hash": phone,
        "password": password,
    })

    response = await client.post("/api/v1/auth/login", json={
        "phone_hash": phone,
        "password": password,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_me_endpoint_with_valid_token(client):
    phone = "f1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    password = "api_me_123"
    await client.post("/api/v1/auth/register", json={
        "phone_hash": phone,
        "password": password,
    })

    login_resp = await client.post("/api/v1/auth/login", json={
        "phone_hash": phone,
        "password": password,
    })
    token = login_resp.json()["access_token"]

    response = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["role"] == "patient"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_me_endpoint_without_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
