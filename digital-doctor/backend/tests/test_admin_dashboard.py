import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.db.base import Base
from src.db.session import get_db
from src.main import app
from src.api.auth_deps import get_current_user
from src.models.user import User, UserRole


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

    # Override auth to return admin user
    async def mock_admin():
        return User(
            id="00000000-0000-0000-0000-000000000001",
            phone_hash="test_admin",
            role=UserRole.ADMIN,
            is_active=True,
        )

    app.dependency_overrides[get_current_user] = mock_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_dashboard_stats(client):
    """Dashboard endpoint returns summary stats for admin user."""
    response = await client.get("/api/v1/admin/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_patients" in data
    assert "active_patients" in data
    assert "total_doctors" in data
    assert "total_departments" in data
    assert "alerts_by_severity" in data
    assert "glucose_control_rate" in data
    assert "patient_registration_trend" in data
    assert isinstance(data["alerts_by_severity"], dict)
    assert isinstance(data["patient_registration_trend"], list)
    # With empty DB, counts should be 0
    assert data["total_patients"] == 0
    assert data["total_doctors"] == 0
    assert data["glucose_control_rate"] == 0.0


@pytest.mark.asyncio
async def test_config_get_set(client):
    """Config endpoints allow getting and setting rule parameters."""
    # Get current config
    response = await client.get("/api/v1/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert "params" in data
    assert "config_version" in data
    assert "versions" in data
    assert "fpg_diagnostic_threshold" in data["params"]
    assert data["params"]["fpg_diagnostic_threshold"] == 7.0

    # Update config
    response = await client.post("/api/v1/admin/config", json={
        "fpg_diagnostic_threshold": 7.5,
        "hba1c_treatment_target": 6.8,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["params"]["fpg_diagnostic_threshold"] == 7.5
    assert data["params"]["hba1c_treatment_target"] == 6.8
    # Other values should remain at defaults
    assert data["params"]["hypoglycemia_threshold"] == 3.9
    assert data["config_version"] > 0

    # Verify get returns updated values
    response = await client.get("/api/v1/admin/config")
    assert response.status_code == 200
    data = response.json()
    assert data["params"]["fpg_diagnostic_threshold"] == 7.5

    # Reset config
    response = await client.post("/api/v1/admin/config/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["params"]["fpg_diagnostic_threshold"] == 7.0
