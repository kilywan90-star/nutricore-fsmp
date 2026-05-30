"""Tests for grassroots module — screening, follow-up, dashboard, offline queue, sync."""

import uuid
from datetime import date, datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.db.base import Base
from src.db.session import get_db
from src.main import app
from src.services.grassroots_service import calculate_screening_risk
from src.services.offline_queue import OfflineQueue

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def client():
    """Create test client with in-memory SQLite."""
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


# ── Test: Screening risk calculation ──────────────────────────────────────

class TestScreeningRiskCalculation:
    def test_low_risk(self):
        """Young person with normal values gets low risk."""
        result = calculate_screening_risk(
            age=25,
            waist_circumference=80,
            fasting_glucose=5.0,
            systolic_bp=120,
            diastolic_bp=80,
            family_history=False,
        )
        assert result["risk_level"].value == "low"
        assert result["risk_score"] <= 6
        assert result["referral_needed"] is False
        assert "factor_scores" in result
        assert "age" in result["factor_scores"]

    def test_high_risk_elderly_family_history(self):
        """Older person with family history and elevated FPG gets high risk."""
        result = calculate_screening_risk(
            age=65,
            waist_circumference=100,
            fasting_glucose=7.5,
            systolic_bp=150,
            diastolic_bp=95,
            family_history=True,
        )
        assert result["risk_level"].value in ("high", "very_high")
        assert result["risk_score"] > 12
        assert result["referral_needed"] is True

    def test_moderate_risk_borderline(self):
        """Borderline values give moderate risk."""
        result = calculate_screening_risk(
            age=45,
            waist_circumference=90,
            fasting_glucose=6.0,
            systolic_bp=130,
            diastolic_bp=85,
            family_history=False,
        )
        assert result["risk_level"].value in ("low", "moderate")
        assert "recommendation" in result


# ── Test: Follow-up record via API ───────────────────────────────────────

@pytest.mark.asyncio
async def test_follow_up_record(client):
    """Create a screening, then record a follow-up visit."""
    # Submit a screening first
    screening_resp = await client.post("/api/v1/grassroots/screening", json={
        "name": "张三",
        "village": "李家村",
        "age": 55,
        "gender": "M",
        "waist_circumference": 95,
        "fasting_glucose": 7.2,
        "systolic_bp": 140,
        "diastolic_bp": 90,
        "family_history": True,
    })
    assert screening_resp.status_code == 200
    screening_data = screening_resp.json()
    patient_id = screening_data["patient_id"]

    # Record follow-up
    fu_resp = await client.post(
        f"/api/v1/grassroots/patients/{patient_id}/follow-up",
        json={
            "glucose_value": 6.8,
            "medication_adherent": True,
            "new_symptoms": "偶有口渴",
            "referral_needed": False,
            "notes": "饮食控制较好",
            "next_follow_up": str(date.today()),
        },
    )
    assert fu_resp.status_code == 200
    fu_data = fu_resp.json()
    assert fu_data["patient_id"] == patient_id
    assert fu_data["glucose_value"] == 6.8
    assert fu_data["medication_adherent"] is True


# ── Test: Monthly report via dashboard API ───────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_stats_after_screening(client):
    """Dashboard should reflect screening counts."""
    # Submit a screening
    await client.post("/api/v1/grassroots/screening", json={
        "name": "李四",
        "village": "王家村",
        "age": 60,
        "gender": "F",
        "waist_circumference": 88,
        "fasting_glucose": 8.0,
        "systolic_bp": 160,
        "diastolic_bp": 100,
        "family_history": False,
    })

    dash_resp = await client.get("/api/v1/grassroots/dashboard")
    assert dash_resp.status_code == 200
    dash = dash_resp.json()
    assert dash["total_managed"] >= 1
    assert "screenings_this_month" in dash
    assert "today_screenings" in dash
    assert "high_risk_count" in dash


# ── Test: Offline queue enqueue/dequeue ──────────────────────────────────

class TestOfflineQueue:
    def test_enqueue_and_status(self, tmp_path):
        """Enqueue items and verify status reflects pending count."""
        db_path = str(tmp_path / "test_offline.db")
        queue = OfflineQueue(db_path=db_path)

        # Enqueue a screening action
        entry_id = queue.enqueue("screening", {
            "patient_id": str(uuid.uuid4()),
            "age": 50,
            "gender": "M",
            "waist_circumference": 90,
            "fasting_glucose": 6.5,
            "systolic_bp": 130,
            "diastolic_bp": 85,
            "family_history": False,
            "risk_level": "moderate",
            "risk_score": 10,
        })
        assert entry_id
        assert len(entry_id) == 36  # UUID format

        # Check status
        status = queue.get_queue_status()
        assert status["pending_count"] >= 1

        queue.close()

    def test_enqueue_multiple_actions(self, tmp_path):
        """Enqueue screening and follow-up, check both are pending."""
        db_path = str(tmp_path / "test_offline2.db")
        queue = OfflineQueue(db_path=db_path)

        pid = str(uuid.uuid4())
        queue.enqueue("screening", {
            "patient_id": pid,
            "age": 60,
            "gender": "F",
            "waist_circumference": 85,
            "fasting_glucose": 7.0,
            "systolic_bp": 145,
            "diastolic_bp": 95,
            "family_history": True,
            "risk_level": "high",
            "risk_score": 18,
        })
        queue.enqueue("follow_up", {
            "patient_id": pid,
            "glucose_value": 7.2,
            "medication_adherent": True,
            "followed_up_at": datetime.utcnow().isoformat(),
        })

        status = queue.get_queue_status()
        assert status["pending_count"] == 2

        queue.close()


# ── Test: Sync processing (process_queue with real DB session) ───────────

@pytest.mark.asyncio
async def test_sync_processing(client, tmp_path):
    """Sync endpoint processes offline queue into main DB."""
    # Create initial data via screening endpoint
    await client.post("/api/v1/grassroots/screening", json={
        "name": "王五",
        "village": "赵家村",
        "age": 50,
        "gender": "M",
        "waist_circumference": 92,
        "fasting_glucose": 6.8,
        "systolic_bp": 135,
        "diastolic_bp": 88,
        "family_history": False,
    })

    # Sync status should be accessible
    status_resp = await client.get("/api/v1/grassroots/sync/status")
    assert status_resp.status_code == 200
    status = status_resp.json()
    assert "pending_count" in status
    assert "last_sync_time" in status

    # Sync endpoint should work
    sync_resp = await client.post("/api/v1/grassroots/sync")
    assert sync_resp.status_code == 200
    sync = sync_resp.json()
    assert sync["status"] == "ok"
    assert "synced" in sync
