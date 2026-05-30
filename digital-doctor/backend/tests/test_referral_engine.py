"""Tests for referral engine — criteria evaluation, target search, referral creation, and clinical summary."""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select as sa_select

from src.db.base import Base
from src.models.patient import Patient, GlucoseRecord, MedicationReminder
from src.models.clinical import LabReport, Alert, AlertSeverity
from src.models.org import (
    Hospital, HospitalLevel, Department, DoctorProfile,
    ReferralRecord, ReferralStatus,
)
from src.services.referral_engine import (
    evaluate_referral_need,
    find_referral_targets,
    create_referral,
)
from src.services.clinical_summary import generate_referral_summary

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_referral_criteria_met(db_session):
    """Test that referral criteria correctly identify patients needing referral."""
    # HbA1c > 9.0 + 3 meds + eGFR < 30
    patient_data = {
        "hba1c": 10.5,
        "medication_count": 3,
        "egfr": 22,
        "has_active_foot_ulcer": False,
        "recent_cvd_event": False,
        "severe_hypoglycemia_episodes": 0,
        "is_pregnant": False,
        "diabetes_type": "type2",
    }
    complication_risks = {}

    result = evaluate_referral_need(patient_data, complication_risks)

    assert result["referral_needed"] is True
    assert result["urgency"] == "urgent"  # eGFR < 30 triggers urgent
    assert result["criteria_met"] >= 2  # HbA1c + eGFR
    assert "eGFR" in result["reason"]
    assert "HbA1c" in result["reason"]


@pytest.mark.asyncio
async def test_referral_criteria_not_met(db_session):
    """Test that well-controlled patients are not flagged for referral."""
    patient_data = {
        "hba1c": 7.2,
        "medication_count": 1,
        "egfr": 95,
        "has_active_foot_ulcer": False,
        "recent_cvd_event": False,
        "severe_hypoglycemia_episodes": 0,
        "is_pregnant": False,
        "diabetes_type": "type2",
    }
    complication_risks = {}

    result = evaluate_referral_need(patient_data, complication_risks)

    assert result["referral_needed"] is False
    assert result["criteria_met"] == 0
    assert result["reason"] == "暂无转诊指征"


@pytest.mark.asyncio
async def test_find_referral_targets(db_session):
    """Test searching for available referral target hospitals."""
    # Seed hospitals with departments
    h1 = Hospital(name="县人民医院", code="XRM001", level=HospitalLevel.II_A, address="县城中心路1号", is_active=True)
    h2 = Hospital(name="市立医院", code="SLYY01", level=HospitalLevel.III_B, address="市辖区解放路100号", is_active=True)
    h3 = Hospital(name="省人民医院", code="SRM001", level=HospitalLevel.III_A, address="省会城市医路1号", is_active=True)
    db_session.add_all([h1, h2, h3])
    await db_session.commit()

    d1 = Department(name="内分泌科", code="NDMKA", hospital_id=h2.id, is_active=True)
    d2 = Department(name="心血管内科", code="XXGNK", hospital_id=h3.id, is_active=True)
    d3 = Department(name="内分泌科", code="NDMKB", hospital_id=h3.id, is_active=True)
    db_session.add_all([d1, d2, d3])
    await db_session.commit()

    # Search for municipal-level endocrinology
    targets = await find_referral_targets(
        patient_location="某县城",
        needed_department="内分泌科",
        target_level="municipal",
        db=db_session,
    )

    assert len(targets) >= 1
    # Should include municipal and above
    target_names = [t["name"] for t in targets]
    assert "市立医院" in target_names or "省人民医院" in target_names


@pytest.mark.asyncio
async def test_create_referral(db_session):
    """Test creating a referral with clinical summary."""
    # Seed source hospital + patient
    h1 = Hospital(name="县医院", code="XYY01", level=HospitalLevel.II_B, address="县城", is_active=True)
    h2 = Hospital(name="市医院", code="SYY01", level=HospitalLevel.III_B, address="市区", is_active=True)
    db_session.add_all([h1, h2])
    await db_session.commit()

    patient = Patient(
        name_hash="test_ref_patient_" + "x" * 20,
        gender="F",
        birth_year=1965,
        diabetes_type="type2",
        diagnosis_date=date(2010, 1, 1),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)
    await db_session.refresh(h1)
    await db_session.refresh(h2)

    # Add medication
    med = MedicationReminder(
        patient_id=patient.id,
        drug_name="二甲双胍",
        dosage="0.5g bid",
        frequency="daily",
        time_of_day=["08:00", "18:00"],
        start_date=date(2024, 1, 1),
        is_active=True,
    )
    db_session.add(med)
    await db_session.commit()

    # Add recent lab
    lab = LabReport(
        patient_id=patient.id,
        report_type="糖化血红蛋白",
        report_date=date(2026, 5, 1),
        results={"hba1c": 10.2},
        ai_interpretation="HbA1c显著升高",
    )
    db_session.add(lab)
    await db_session.commit()

    # Generate summary first
    summary = await generate_referral_summary(patient.id, db_session)
    assert "patient_demographics" in summary
    assert summary["medication_count"] >= 1

    from_doctor_id = uuid.uuid4()

    # Create referral
    result = await create_referral(
        patient_id=patient.id,
        from_hospital_id=h1.id,
        from_doctor_id=from_doctor_id,
        to_hospital_id=h2.id,
        urgency="urgent",
        target_department="内分泌科",
        target_level="municipal",
        reason="HbA1c持续不达标",
        clinical_summary=summary,
        db=db_session,
    )

    assert result["status"] == "pending"
    assert result["urgency"] == "urgent"
    assert result["from_hospital_name"] == "县医院"
    assert result["to_hospital_name"] == "市医院"
    assert result["target_department"] == "内分泌科"
    assert result["clinical_summary"] is not None

    # Verify same-hospital rejection
    with pytest.raises(ValueError, match="same hospital"):
        await create_referral(
            patient_id=patient.id,
            from_hospital_id=h1.id,
            from_doctor_id=from_doctor_id,
            to_hospital_id=h1.id,
            urgency="routine",
            reason="test",
            clinical_summary=summary,
            db=db_session,
        )


@pytest.mark.asyncio
async def test_clinical_summary_generation(db_session):
    """Test comprehensive clinical summary generation."""
    patient = Patient(
        name_hash="test_summary_patient_" + "x" * 15,
        gender="M",
        birth_year=1970,
        diabetes_type="type2",
        diagnosis_date=date(2015, 6, 1),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    # Add medications
    meds = [
        MedicationReminder(
            patient_id=patient.id,
            drug_name="二甲双胍",
            dosage="0.5g bid",
            frequency="daily",
            time_of_day=["08:00", "18:00"],
            start_date=date(2024, 1, 1),
            is_active=True,
        ),
        MedicationReminder(
            patient_id=patient.id,
            drug_name="达格列净",
            dosage="10mg qd",
            frequency="daily",
            time_of_day=["08:00"],
            start_date=date(2024, 6, 1),
            is_active=True,
        ),
        MedicationReminder(
            patient_id=patient.id,
            drug_name="甘精胰岛素",
            dosage="16U qn",
            frequency="daily",
            time_of_day=["22:00"],
            start_date=date(2025, 1, 1),
            is_active=True,
        ),
    ]
    db_session.add_all(meds)
    await db_session.commit()

    # Add glucose records
    glucose_vals = [8.5, 9.2, 7.8, 10.1, 11.2, 6.5, 5.8, 12.0, 13.5, 8.0]
    for i, val in enumerate(glucose_vals):
        gr = GlucoseRecord(
            patient_id=patient.id,
            value_mmol_l=val,
            measure_type="fpg" if i % 2 == 0 else "ppg",
            recorded_at=datetime.utcnow() - timedelta(days=len(glucose_vals) - i),
        )
        db_session.add(gr)
    await db_session.commit()

    # Add lab reports — use a date within the last 3 months
    lab = LabReport(
        patient_id=patient.id,
        report_type="糖化血红蛋白",
        report_date=date(2026, 5, 1),
        results={"hba1c": 10.5, "fpj": 8.2, "egfr": 75},
        ai_interpretation="HbA1c升高，血糖控制不佳",
    )
    db_session.add(lab)
    await db_session.commit()

    # Add alerts for complication tracking
    alert = Alert(
        patient_id=patient.id,
        alert_type="complication",
        severity=AlertSeverity.WARNING,
        title="糖尿病肾病风险",
        detail="基于eGFR下降趋势，存在糖尿病肾病早期风险",
    )
    db_session.add(alert)
    await db_session.commit()

    # Generate summary
    summary = await generate_referral_summary(patient.id, db_session)

    # Verify structure
    assert "patient_demographics" in summary
    assert summary["patient_demographics"]["gender"] == "M"
    assert summary["patient_demographics"]["diabetes_type"] == "type2"
    assert summary["patient_demographics"]["duration_years"] is not None

    assert "current_medications" in summary
    assert summary["medication_count"] == 3

    assert "glucose_control_summary" in summary
    gcs = summary["glucose_control_summary"]
    assert gcs["total_records"] == 10
    assert gcs["avg_mmol_l"] is not None
    assert gcs["in_range_pct"] is not None
    assert "trend" in gcs

    assert "recent_lab_results" in summary
    assert len(summary["recent_lab_results"]) >= 1

    assert "hba1c_history" in summary
    assert len(summary["hba1c_history"]) >= 1
    assert summary["hba1c_history"][0]["value"] == 10.5

    assert "complication_status" in summary
    assert summary["complication_status"]["has_known_complications"] is True

    assert "questions_for_receiving_physician" in summary
    assert len(summary["questions_for_receiving_physician"]) >= 1
