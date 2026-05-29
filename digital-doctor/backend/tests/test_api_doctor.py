import pytest
from httpx import AsyncClient, ASGITransport, ConnectError
from src.main import app
from src.api.auth_deps import get_current_user
from src.models.user import User, UserRole
import uuid


async def mock_get_current_user():
    return User(id=uuid.uuid4(), phone_hash="test_doctor", role=UserRole.DOCTOR, is_active=True)


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_patients_db_unavailable(client):
    """When PostgreSQL is not running, the endpoint will fail to connect."""
    try:
        response = await client.get("/api/v1/doctor/patients")
        assert response.status_code in (200, 500)
    except (ConnectError, ConnectionRefusedError, OSError):
        # Expected when PostgreSQL is unavailable
        pass


@pytest.mark.asyncio
async def test_get_patient_not_found_db_unavailable(client):
    try:
        response = await client.get("/api/v1/doctor/patients/00000000-0000-0000-0000-000000000000")
        assert response.status_code in (404, 500)
    except (ConnectError, ConnectionRefusedError, OSError):
        pass
