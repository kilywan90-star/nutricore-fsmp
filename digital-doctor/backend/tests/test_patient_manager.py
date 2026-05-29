import pytest
from datetime import date, datetime
from src.models.patient import Patient, GlucoseRecord
from src.models.clinical import LabReport, Alert


@pytest.mark.asyncio
async def test_get_patient_list_empty(db_session):
    from src.services.patient_manager import get_patient_list
    result = await get_patient_list(db_session)
    assert result["total"] == 0
    assert result["items"] == []


@pytest.mark.asyncio
async def test_get_patient_detail_not_found(db_session):
    from src.services.patient_manager import get_patient_detail
    result = await get_patient_detail(db_session, "00000000-0000-0000-0000-000000000000")
    assert result is None


@pytest.mark.asyncio
async def test_get_patient_detail_with_data(db_session):
    from src.services.patient_manager import get_patient_detail

    patient = Patient(
        name_hash="test_hash",
        gender="M",
        birth_year=1970,
        diabetes_type="type2",
        diagnosis_date=date(2020, 1, 15),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()

    glucose = GlucoseRecord(
        patient_id=patient.id,
        value_mmol_l=6.5,
        measure_type="fasting",
        recorded_at=datetime(2026, 5, 30, 7, 0),
    )
    db_session.add(glucose)
    await db_session.commit()

    detail = await get_patient_detail(db_session, str(patient.id))
    assert detail is not None
    assert detail["gender"] == "M"
    assert detail["birth_year"] == 1970
    assert len(detail["glucose_records"]) >= 1
    assert detail["glucose_records"][0]["value_mmol_l"] == 6.5
