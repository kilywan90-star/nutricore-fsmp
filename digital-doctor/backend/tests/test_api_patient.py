import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_risk_assessment_endpoint(client):
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
    assert "risk_level" in data
    assert data["score"] >= 15
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_report_interpret_endpoint(client):
    response = await client.post("/api/v1/patient/report-interpret", json={
        "report_type": "blood_glucose_panel",
        "results": {"fpg": 6.5, "hba1c": 7.2},
    })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("impaired", "abnormal")


@pytest.mark.asyncio
async def test_glucose_stats_endpoint(client):
    response = await client.post("/api/v1/patient/glucose-stats", json=[6.5, 7.2, 5.8, 8.0, 6.1])
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert data["avg"] is not None


@pytest.mark.asyncio
async def test_health_coach_endpoint(client):
    response = await client.post("/api/v1/patient/health-coach", json={
        "message": "我最近血糖有点高",
        "recent_fpg": [6.5, 6.8, 7.0],
        "hba1c": 7.2,
        "medications": ["二甲双胍"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "is_urgent" in data


@pytest.mark.asyncio
async def test_risk_assessment_validation(client):
    response = await client.post("/api/v1/patient/risk-assessment", json={
        "age": 10,  # below minimum 18
        "bmi": 28.5,
        "waist_circumference": 95,
        "family_history": True,
        "physical_activity": "low",
        "fasting_glucose": 6.8,
        "has_hypertension": True,
    })
    assert response.status_code == 422
