# digital-doctor/backend/tests/test_patient_manager.py
import pytest
from datetime import date, datetime
from src.services.patient_manager import get_patient_list, get_patient_detail
from src.models.patient import Patient


@pytest.mark.asyncio
async def test_get_patient_list_with_pagination(db_session):
    # Create test patients
    for i in range(3):
        patient = Patient(
            name_hash=f"hash{i}",
            gender="M" if i % 2 == 0 else "F",
            birth_year=1970 + i * 5,
            diabetes_type="type2",
            hba1c_target=7.0,
        )
        db_session.add(patient)
    await db_session.commit()

    result = await get_patient_list(db_session, page=1, page_size=2)
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_get_patient_detail(db_session):
    patient = Patient(
        name_hash="hash_detail",
        gender="F",
        birth_year=1975,
        diabetes_type="type2",
        diagnosis_date=date(2020, 3, 15),
        hba1c_target=7.0,
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    detail = await get_patient_detail(db_session, str(patient.id))
    assert detail is not None
    assert detail["gender"] == "F"
    assert detail["birth_year"] == 1975
    assert detail["diabetes_type"] == "type2"
    assert detail["hba1c_target"] == 7.0
    assert detail["diagnosis_date"] == "2020-03-15"
    assert "glucose_records" in detail
    assert "lab_reports" in detail
    assert "alerts" in detail
