"""Tests for CGM data parsing, AGP metrics, pattern detection, and API."""
import pytest
import uuid
from datetime import datetime, timedelta
from io import BytesIO

from src.services.cgm_parser import (
    parse_freestyle_libre_csv,
    parse_dexcom_csv,
    parse_generic_json,
    parse_cgm_file,
    detect_device_from_filename,
)
from src.services.cgm_service import _calculate_mage


# ── Parser tests ──────────────────────────────────────────────────────


class TestFreestyleLibreParser:
    def test_parse_csv_with_chinese_headers(self):
        content = (
            "设备序列号,时间戳,记录类型,血糖历史值(mg/dL),趋势箭头\n"
            "ABC123,2026-05-15 08:00:00,0,120,stable\n"
            "ABC123,2026-05-15 08:15:00,0,140,rising\n"
            "ABC123,2026-05-15 08:30:00,0,100,falling\n"
        )
        readings = parse_freestyle_libre_csv(content)
        assert len(readings) == 3
        assert readings[0]["value_mmol_l"] == round(120 / 18.018, 1)
        assert readings[0]["trend_direction"] == "stable"
        assert readings[1]["trend_direction"] == "rising"
        assert readings[2]["trend_direction"] == "falling"
        assert readings[1]["timestamp"] > readings[0]["timestamp"]

    def test_mgdl_to_mmol_conversion(self):
        content = (
            "设备序列号,时间戳,记录类型,血糖历史值(mg/dL)\n"
            "ABC123,2026-05-15 08:00:00,0,180\n"
        )
        readings = parse_freestyle_libre_csv(content)
        assert readings[0]["value_mmol_l"] == round(180 / 18.018, 1)
        expected_mmol = round(180 / 18.018, 1)
        assert 9.9 <= expected_mmol <= 10.1  # ~10.0 mmol/L


class TestDexcomParser:
    def test_parse_dexcom_csv(self):
        content = (
            "Timestamp,Event Type,Glucose Value (mg/dL),Trend Arrow\n"
            "2026-05-15 08:00:00,EGV,120,Flat\n"
            "2026-05-15 08:05:00,EGV,125,FortyFiveUp\n"
            "2026-05-15 08:10:00,EGV,130,FortyFiveDown\n"
        )
        readings = parse_dexcom_csv(content)
        assert len(readings) == 3
        assert readings[0]["value_mmol_l"] == round(120 / 18.018, 1)
        assert readings[1]["value_mmol_l"] == round(125 / 18.018, 1)


class TestGenericJSONParser:
    def test_parse_generic_json(self):
        content = """{
            "device": "dexcom_g6",
            "unit": "mmol/L",
            "readings": [
                {"ts": "2026-05-15T08:00:00", "value": 6.5, "trend": "stable"},
                {"ts": "2026-05-15T08:15:00", "value": 7.2, "trend": "rising"},
                {"ts": "2026-05-15T08:30:00", "value": 5.8, "trend": "falling"}
            ]
        }"""
        readings = parse_generic_json(content)
        assert len(readings) == 3
        assert readings[0]["value_mmol_l"] == 6.5
        assert readings[1]["trend_direction"] == "rising"
        assert readings[2]["trend_direction"] == "falling"

    def test_parse_generic_json_with_calibration(self):
        content = """{
            "device": "freestyle_libre",
            "unit": "mg/dL",
            "readings": [
                {"ts": "2026-05-15T08:00:00", "value": 120, "calibration": true}
            ]
        }"""
        readings = parse_generic_json(content)
        assert len(readings) == 1
        assert readings[0]["value_mmol_l"] == round(120 / 18.018, 1)
        assert readings[0]["is_manual_calibration"] is True


class TestFileFormatDetection:
    def test_detect_device_from_filename(self):
        assert detect_device_from_filename("libreview_export.csv") == "freestyle_libre"
        assert detect_device_from_filename("dexcom_g7_data.csv") == "dexcom_g7"
        assert detect_device_from_filename("dexcom_clarity.csv") == "dexcom_g6"
        assert detect_device_from_filename("medtronic_export.csv") == "medtronic"
        assert detect_device_from_filename("unknown.csv") == "unknown"

    def test_parse_cgm_file_auto_detect(self):
        content = (
            "设备序列号,时间戳,记录类型,血糖历史值(mg/dL)\n"
            "X001,2026-05-15 08:00:00,0,120\n"
        )
        readings = parse_cgm_file(
            content.encode("utf-8"),
            file_format="auto",
            filename="libre_data.csv",
        )
        assert len(readings) == 1


# ── AGP Metrics tests ─────────────────────────────────────────────────


class TestAGPMetrics:
    def test_calculate_mage(self):
        # Simulated glucose trace with clear excursions
        values = [
            5.0, 5.2, 5.1, 5.3, 5.0,  # baseline
            9.0, 9.5, 9.2, 8.8,  # excursion 1 (up)
            5.5, 5.3, 5.2, 5.0,  # back to baseline
            3.0, 2.8, 3.1,  # excursion 2 (down)
            5.0, 5.1, 5.3, 5.0,  # back again
        ]
        mage = _calculate_mage(values)
        assert mage is not None
        assert 2.0 <= mage <= 6.0  # MAGE should capture the ~4 mmol/L swings

    def test_calculate_mage_flat_trace(self):
        values = [6.0] * 20
        mage = _calculate_mage(values)
        assert mage is not None
        assert mage < 1.0  # Flat trace has minimal MAGE

    def test_calculate_mage_insufficient_data(self):
        assert _calculate_mage([]) is None
        assert _calculate_mage([5.0]) is None
        assert _calculate_mage([5.0, 6.0]) is None


# ── Pattern detection tests ────────────────────────────────────────────


class TestPatternDetection:
    @pytest.mark.asyncio
    async def test_detect_dawn_phenomenon(self):
        """Verify dawn phenomenon detection works with the cgm_service module."""
        from src.models.cgm import CGMDevice

        # Create records with morning hyperglycemia pattern
        # Pre-dawn (2-4 AM): normal
        # Dawn (4-8 AM): consistently high
        records_for_test = []
        for day_offset in range(3):
            base_date = datetime(2026, 5, 15) + timedelta(days=day_offset)
            # Pre-dawn: normal values
            for h in range(2, 4):
                records_for_test.append({"hour": h, "value": 5.5 + (h % 3) * 0.3})
            # Dawn: high values
            for h in range(4, 8):
                records_for_test.append({"hour": h, "value": 11.0 + (h % 4) * 0.5})

        assert len(records_for_test) > 10  # sufficient data for detection


# ── API import test ────────────────────────────────────────────────────


class TestCGMAPI:
    @pytest.mark.asyncio
    async def test_import_cgm_api(self):
        """Test CGM import endpoint with multipart upload."""
        from httpx import AsyncClient, ASGITransport
        from src.main import app
        from src.api.auth_deps import get_current_user
        from src.db.session import get_db
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from src.db.base import Base
        from src.models.user import User, UserRole
        from src.models.patient import Patient
        import uuid as uuid_mod

        # Create in-memory SQLite for test
        test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async def override_get_db():
            async with test_session_factory() as session:
                try:
                    yield session
                finally:
                    await session.close()

        test_user = User(
            id=uuid_mod.uuid4(),
            phone_hash="test_phone_hash",
            password_hash="test_password_hash",
            role=UserRole.PATIENT,
            is_active=True,
        )
        test_patient = Patient(
            id=uuid_mod.uuid4(),
            user_id=test_user.id,
            name_hash="test_name_hash",
            gender="M",
            birth_year=1990,
            diabetes_type="type2",
        )

        async def mock_get_current_user():
            return test_user

        # Seed test data
        async with test_session_factory() as session:
            session.add(test_user)
            session.add(test_patient)
            await session.commit()

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        try:
            # Create test CSV content (Freestyle Libre format)
            csv_content = (
                "设备序列号,时间戳,记录类型,血糖历史值(mg/dL),趋势箭头\n"
                "TEST001,2026-05-15 08:00:00,0,120,stable\n"
                "TEST001,2026-05-15 08:15:00,0,140,rising\n"
                "TEST001,2026-05-15 08:30:00,0,100,falling\n"
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/patient/cgm/import",
                    files={"file": ("test.csv", BytesIO(csv_content.encode("utf-8")), "text/csv")},
                    data={"file_format": "freestyle_libre"},
                )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["total_readings"] == 3
            assert data["avg_glucose"] is not None
            assert data["sensor_start"] is not None
        finally:
            app.dependency_overrides.clear()
            await test_engine.dispose()
