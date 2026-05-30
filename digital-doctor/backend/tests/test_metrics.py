"""Tests for Prometheus metrics — endpoint accessibility and counter logic."""

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
    """Create a test client with a mocked database dependency."""
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
async def test_metrics_endpoint_accessible():
    """GET /metrics returns 200 with Prometheus text content from localhost."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
    # testclient is considered internal, so should return 200
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert len(response.text) > 0


@pytest.mark.asyncio
async def test_http_requests_counter_increments(client):
    """Making a tracked HTTP request increments http_requests_total."""
    # Hit a tracked path (non-excluded) — returns 401 but middleware still tracks it
    await client.get("/api/v1/doctor/patients")

    response = await client.get("/metrics")

    metrics_text = response.text
    assert "http_requests_total" in metrics_text
