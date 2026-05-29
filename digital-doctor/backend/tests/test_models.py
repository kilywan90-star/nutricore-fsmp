# digital-doctor/backend/tests/test_models.py
import pytest
from datetime import date, datetime
from src.models.patient import Patient, GlucoseRecord, MedicationReminder
from src.models.clinical import LabReport, Alert
from src.models.user import User


@pytest.mark.asyncio
async def test_create_patient(db_session):
    patient = Patient(
        name_hash="abc123",
        gender="M",
        birth_year=1970,
        diabetes_type="type2",
        diagnosis_date=date(2020, 3, 15),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    assert patient.id is not None
    assert patient.diabetes_type == "type2"
    assert patient.hba1c_target == 7.0


@pytest.mark.asyncio
async def test_create_glucose_record(db_session):
    patient = Patient(name_hash="hash1", gender="F", birth_year=1980, diabetes_type="type2")
    db_session.add(patient)
    await db_session.commit()

    record = GlucoseRecord(
        patient_id=patient.id,
        value_mmol_l=7.8,
        measure_type="fasting",
        recorded_at=datetime(2026, 5, 30, 7, 0),
    )
    db_session.add(record)
    await db_session.commit()

    assert record.value_mmol_l == 7.8
    assert record.measure_type == "fasting"


@pytest.mark.asyncio
async def test_create_medication_reminder(db_session):
    patient = Patient(name_hash="hash2", gender="M", birth_year=1965, diabetes_type="type2")
    db_session.add(patient)
    await db_session.commit()

    reminder = MedicationReminder(
        patient_id=patient.id,
        drug_name="二甲双胍",
        dosage="500mg",
        frequency="bid",
        time_of_day=["08:00", "18:00"],
        start_date=date(2026, 5, 30),
    )
    db_session.add(reminder)
    await db_session.commit()

    assert reminder.drug_name == "二甲双胍"
    assert len(reminder.time_of_day) == 2


@pytest.mark.asyncio
async def test_create_lab_report(db_session):
    patient = Patient(name_hash="hash3", gender="F", birth_year=1975, diabetes_type="type2")
    db_session.add(patient)
    await db_session.commit()

    report = LabReport(
        patient_id=patient.id,
        report_type="blood_glucose_panel",
        report_date=date(2026, 5, 28),
        results={"fpg": 6.5, "hba1c": 7.2, "ppg_2h": 10.1},
        ai_interpretation="",
    )
    db_session.add(report)
    await db_session.commit()

    assert report.results["hba1c"] == 7.2


@pytest.mark.asyncio
async def test_create_alert(db_session):
    patient = Patient(name_hash="hash4", gender="M", birth_year=1960, diabetes_type="type2")
    db_session.add(patient)
    await db_session.commit()

    alert = Alert(
        patient_id=patient.id,
        alert_type="glucose_high",
        severity="warning",
        title="空腹血糖偏高",
        detail="连续3天空腹血糖 > 7.0mmol/L",
        reference_guideline="中国2型糖尿病防治指南(2024版) §6.2",
    )
    db_session.add(alert)
    await db_session.commit()

    assert alert.severity == "warning"
    assert alert.acknowledged is False
