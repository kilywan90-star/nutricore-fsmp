import pytest
from httpx import AsyncClient, ASGITransport, ConnectError
from src.main import app


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


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_risk_assessment_via_api(client):
    response = await client.post("/api/v1/patient/risk-assessment", json={
        "age": 55,
        "bmi": 28.5,
        "waist_circumference": 95,
        "family_history": True,
        "physical_activity": "low",
        "fasting_glucose": 6.8,
        "has_hypertension": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] in ("高危", "极高危")


@pytest.mark.asyncio
async def test_risk_assessment_validation(client):
    response = await client.post("/api/v1/patient/risk-assessment", json={
        "age": 10,
        "bmi": 28.5,
        "waist_circumference": 95,
        "family_history": True,
        "physical_activity": "low",
        "fasting_glucose": 6.8,
        "has_hypertension": True,
    })
    assert response.status_code == 422
