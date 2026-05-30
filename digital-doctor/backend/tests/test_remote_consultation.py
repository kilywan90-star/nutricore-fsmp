"""Tests for remote consultation — request, AI summary preparation, and outcome recording."""

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
    Hospital, HospitalLevel, Department,
    ConsultationSession, ConsultationStatus,
)
from src.services.remote_consultation import (
    prepare_consultation,
    create_consultation_session,
    record_consultation,
    list_consultations,
    get_consultation,
)

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
async def test_consultation_request_creation(db_session):
    """Test creating a remote consultation request with AI-prepared summary."""
    # Seed patient with data
    patient = Patient(
        name_hash="test_consult_patient_" + "x" * 16,
        gender="F",
        birth_year=1980,
        diabetes_type="type2",
        diagnosis_date=date(2018, 5, 1),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

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

    doctor_id = uuid.uuid4()

    # Create consultation session
    session_data = await create_consultation_session(
        patient_id=patient.id,
        requesting_doctor_id=doctor_id,
        clinical_question="该患者HbA1c持续不达标，已使用三联药物，是否需要启用胰岛素治疗？",
        db=db_session,
    )

    assert session_data["status"] == "requested"
    assert session_data["patient_id"] == str(patient.id)
    assert session_data["requesting_doctor_id"] == str(doctor_id)
    assert session_data["clinical_question"] == "该患者HbA1c持续不达标，已使用三联药物，是否需要启用胰岛素治疗？"
    assert session_data["ai_prepared_summary"] is not None

    # Verify AI summary contents
    ai_summary = session_data["ai_prepared_summary"]
    assert "clinical_summary" in ai_summary
    assert "relevant_guidelines" in ai_summary
    assert "suggested_differentials" in ai_summary
    assert len(ai_summary["relevant_guidelines"]) >= 1  # At least core guideline


@pytest.mark.asyncio
async def test_prepare_consultation_summary(db_session):
    """Test AI-prepared consultation materials are comprehensive."""
    patient = Patient(
        name_hash="test_prep_patient_" + "x" * 18,
        gender="M",
        birth_year=1960,
        diabetes_type="type1",
        diagnosis_date=date(2005, 3, 1),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    # Add glucose records showing poor control
    for i, val in enumerate([12.0, 13.5, 15.0, 11.2, 14.8, 10.5, 9.8, 16.2]):
        gr = GlucoseRecord(
            patient_id=patient.id,
            value_mmol_l=val,
            measure_type="fpg" if i % 2 == 0 else "ppg",
            recorded_at=datetime.utcnow() - timedelta(days=8 - i),
        )
        db_session.add(gr)
    await db_session.commit()

    # Add alert for complication
    alert = Alert(
        patient_id=patient.id,
        alert_type="complication",
        severity=AlertSeverity.WARNING,
        title="糖尿病肾病",
        detail="eGFR下降，存在糖尿病肾病风险",
    )
    db_session.add(alert)
    await db_session.commit()

    prepared = await prepare_consultation(
        patient_id=patient.id,
        clinical_question="如何调整胰岛素方案以降低低血糖风险？",
        db=db_session,
    )

    assert "clinical_summary" in prepared
    assert "relevant_guidelines" in prepared
    assert "suggested_differentials" in prepared
    assert "clinical_question" in prepared

    # Verify that guidelines match the keywords in question
    guideline_titles = [g["title"] for g in prepared["relevant_guidelines"]]
    has_insulin = any("胰岛素" in t for t in guideline_titles)
    assert has_insulin  # "胰岛素" matches "胰岛素治疗" in guidelines_db

    # Differential should include hypo-related suggestions
    diffs = prepared["suggested_differentials"]
    assert len(diffs) >= 1


@pytest.mark.asyncio
async def test_record_consultation_outcome(db_session):
    """Test recording consultation outcome and completing the session."""
    patient = Patient(
        name_hash="test_outcome_patient_" + "x" * 15,
        gender="F",
        birth_year=1975,
        diabetes_type="type2",
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    doctor_id = uuid.uuid4()

    # Create session first
    session_data = await create_consultation_session(
        patient_id=patient.id,
        requesting_doctor_id=doctor_id,
        clinical_question="是否需要加用SGLT2抑制剂？",
        db=db_session,
    )
    session_id = uuid.UUID(session_data["id"])

    # Record notes
    updated = await record_consultation(
        session_id=session_id,
        notes="讨论结果：患者eGFR 55，可以使用SGLT2抑制剂，建议起始达格列净10mg qd。",
        outcome="同意加用达格列净10mg qd，定期监测eGFR。",
        db=db_session,
    )

    assert updated["status"] == "completed"
    assert updated["consultation_notes"] == "讨论结果：患者eGFR 55，可以使用SGLT2抑制剂，建议起始达格列净10mg qd。"
    assert updated["outcome"] == "同意加用达格列净10mg qd，定期监测eGFR。"
    assert updated["completed_at"] is not None

    # Verify via get
    detail = await get_consultation(session_id, db_session)
    assert detail["status"] == "completed"
    assert detail["outcome"] is not None

    # List should show completed
    listing = await list_consultations(db=db_session, doctor_id=doctor_id)
    assert listing["total"] >= 1
    found = [i for i in listing["items"] if i["id"] == session_data["id"]]
    assert len(found) == 1
    assert found[0]["status"] == "completed"
