"""Tests for medical record generator, record service, and templates."""
import pytest
import uuid
from unittest.mock import AsyncMock, patch

from src.services.record_generator import (
    generate_soap_note,
    generate_discharge_summary,
    _fallback_soap,
    _fallback_discharge,
    _soap_to_markdown,
    _discharge_to_markdown,
)
from src.services.record_templates import (
    SOAP_SYSTEM,
    SOAP_USER_TEMPLATE,
    DISCHARGE_SYSTEM,
    DISCHARGE_USER_TEMPLATE,
)
from src.services.record_service import (
    create_record,
    get_records,
    get_record,
    update_record,
    finalize_record,
)
from src.models.records import MedicalRecord, RecordType, RecordStatus


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def soap_content():
    return {
        "subjective": "主诉：多饮多尿3个月。现病史：患者近3月出现多饮多尿。",
        "objective": "空腹血糖7.8mmol/L，HbA1c 7.5%，BMI 27.0。",
        "assessment": "诊断：2型糖尿病。基于《中国2型糖尿病防治指南(2024版)》。",
        "plan": "用药方案：二甲双胍500mg bid。建议每3月复查HbA1c。",
        "markdown": "### S\n主诉内容\n### O\n客观数据\n### A\n评估\n### P\n计划\n",
    }


@pytest.fixture
def encounter_data():
    return {
        "pre_consult_summary": {
            "chief_complaint": "多饮多尿3个月",
            "present_illness": "近3月体重下降5kg",
        },
        "lab_results": {"fpg": 7.8, "hba1c": 7.5},
        "glucose_records": [
            {"measure_type": "fasting", "value_mmol_l": 7.8, "recorded_at": "2024-01-15T08:00:00"},
        ],
        "diagnosis_info": {"primary_diagnosis": {"type": "2型糖尿病", "confidence": "high"}},
        "medications": [{"drug_name": "二甲双胍", "dosage": "500mg", "frequency": "bid"}],
    }


@pytest.fixture
def admission_data():
    return {
        "admission_date": "2024-01-10",
        "chief_complaint": "血糖控制不佳2周",
        "admission_diagnosis": "2型糖尿病，血糖控制不良",
        "hospital_course": "入院后调整降糖方案，血糖逐日改善",
        "lab_results": {"fpg": 9.2, "hba1c": 8.8},
        "treatment_plan": "胰岛素泵强化治疗+二甲双胍",
        "discharge_status": "血糖达标，无不适",
    }


# ── Test: SOAP generation returns 4 sections ─────────────────────────────

@pytest.mark.asyncio
async def test_soap_generation_returns_4_sections():
    """SOAP generation should return subjective, objective, assessment, plan."""
    result = _fallback_soap({"pre_consult_summary": "test"})
    assert "subjective" in result
    assert "objective" in result
    assert "assessment" in result
    assert "plan" in result
    assert len(result) == 4


# ── Test: Discharge summary has required sections ─────────────────────────

@pytest.mark.asyncio
async def test_discharge_summary_has_required_sections():
    """Discharge summary should include admission, course, diagnosis, orders, follow-up."""
    result = _fallback_discharge({"chief_complaint": "test"})
    assert "admission_summary" in result
    assert "hospital_course" in result
    assert "discharge_diagnosis" in result
    assert "discharge_orders" in result
    assert "follow_up_plan" in result
    assert len(result) == 5


# ── Test: LLM fallback produces valid structure ───────────────────────────

def test_llm_fallback_produces_valid_structure(encounter_data):
    """Fallback SOAP should produce non-empty content with valid structure."""
    result = _fallback_soap(encounter_data)
    # All sections should be non-empty strings
    assert isinstance(result["subjective"], str) and len(result["subjective"]) > 0
    assert isinstance(result["objective"], str) and len(result["objective"]) > 0
    assert isinstance(result["assessment"], str) and len(result["assessment"]) > 0
    assert isinstance(result["plan"], str) and len(result["plan"]) > 0
    # Assessment should reference the guideline
    assert "指南" in result["assessment"]


def test_markdown_generation():
    """SOAP content should convert to valid markdown."""
    content = {
        "subjective": "S test",
        "objective": "O test",
        "assessment": "A test",
        "plan": "P test",
    }
    md = _soap_to_markdown(content)
    assert "### S" in md
    assert "S test" in md
    assert "### O" in md
    assert "### A" in md
    assert "### P" in md


# ── Test: Record CRUD via service ────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_crud_via_service(db_session, soap_content):
    """Create, read, list operations should work correctly."""
    pid = uuid.uuid4()
    did = uuid.uuid4()

    # Create
    content = dict(soap_content)
    record = await create_record(pid, did, RecordType.SOAP, content, db_session)
    assert record.id is not None
    assert record.patient_id == pid
    assert record.doctor_id == did
    assert record.record_type == RecordType.SOAP
    assert record.status == RecordStatus.DRAFT
    assert record.version == 1
    assert record.content["subjective"] == content["subjective"]

    # Get
    fetched = await get_record(record.id, db_session)
    assert fetched is not None
    assert str(fetched.id) == str(record.id)

    # List
    records = await get_records(pid, db_session)
    assert len(records) == 1
    assert records[0].id == record.id

    # Filter by type
    soap_records = await get_records(pid, db_session, RecordType.SOAP)
    assert len(soap_records) == 1
    discharge_records = await get_records(pid, db_session, RecordType.DISCHARGE)
    assert len(discharge_records) == 0


# ── Test: Record versioning on edit ───────────────────────────────────────

@pytest.mark.asyncio
async def test_record_versioning_on_edit(db_session, soap_content):
    """Updating a record should save the previous version to history."""
    pid = uuid.uuid4()
    did = uuid.uuid4()

    content = dict(soap_content)
    record = await create_record(pid, did, RecordType.SOAP, content, db_session)
    original_version = record.version
    original_content = dict(record.content)

    # Edit
    new_content = {**original_content, "subjective": "修改后的主诉内容"}
    updated = await update_record(
        record.id,
        {"content": new_content, "markdown": "new markdown"},
        did,
        db_session,
    )

    assert updated is not None
    assert updated.version == original_version + 1
    assert updated.content["subjective"] == "修改后的主诉内容"
    assert updated.markdown == "new markdown"

    # Version history should contain the original
    assert len(updated.versions) == 1
    saved = updated.versions[0]
    assert saved["version"] == original_version
    assert saved["content"]["subjective"] == original_content["subjective"]
    assert saved["edited_by"] == str(did)


# ── Test: Record finalize ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_finalize(db_session, soap_content):
    """Finalizing a record should change status to FINALIZED."""
    pid = uuid.uuid4()
    did = uuid.uuid4()

    content = dict(soap_content)
    record = await create_record(pid, did, RecordType.SOAP, content, db_session)
    assert record.status == RecordStatus.DRAFT

    finalized = await finalize_record(record.id, did, db_session)
    assert finalized is not None
    assert finalized.status == RecordStatus.FINALIZED

    # Refetch to confirm persistence
    refetched = await get_record(record.id, db_session)
    assert refetched.status == RecordStatus.FINALIZED


# ── Test: Prompt templates ────────────────────────────────────────────────

def test_soap_system_prompt_exists():
    """SOAP system prompt should contain key clinical elements."""
    assert "SOAP" in SOAP_SYSTEM
    assert "病历书写" in SOAP_SYSTEM
    assert "subjective" in SOAP_SYSTEM.lower()
    assert "objective" in SOAP_SYSTEM.lower()
    assert "assessment" in SOAP_SYSTEM.lower()
    assert "plan" in SOAP_SYSTEM.lower()


def test_soap_user_template_fills_correctly():
    """SOAP user template should fill encounter data without crashing."""
    result = SOAP_USER_TEMPLATE.format(
        pre_consult_summary="主诉：多饮多尿3个月",
        lab_results="- fpg: 7.8 mmol/L",
        glucose_data="- fasting: 7.8 mmol/L",
        diagnosis_info="2型糖尿病",
        medications="- 二甲双胍 500mg bid",
    )
    assert "多饮多尿" in result
    assert "7.8" in result
    assert "2型糖尿病" in result
    assert "二甲双胍" in result


def test_discharge_system_prompt_exists():
    """Discharge system prompt should contain key clinical elements."""
    assert "出院小结" in DISCHARGE_SYSTEM
    assert "discharge" in DISCHARGE_SYSTEM.lower()
    assert "admission_summary" in DISCHARGE_SYSTEM.lower() or "入院" in DISCHARGE_SYSTEM


# ── Test: LLM call is mocked and produces valid SOAP ─────────────────────

@pytest.mark.asyncio
async def test_generate_soap_uses_llm_and_returns_valid(encounter_data):
    """SOAP generation via LLM should return structured content."""
    mock_response = (
        '{"subjective": "主诉：多饮多尿", '
        '"objective": "FPG 7.8 mmol/L", '
        '"assessment": "2型糖尿病", '
        '"plan": "二甲双胍+BMI随访"}'
    )

    with patch("src.services.record_generator.llm_client.chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = mock_response
        with patch("src.services.record_generator.llm_client.sanitize_clinical_data") as mock_san:
            mock_san.return_value = encounter_data
            result = await generate_soap_note(encounter_data)

    assert "subjective" in result
    assert "objective" in result
    assert "assessment" in result
    assert "plan" in result
    assert "markdown" in result
    assert "### S" in result["markdown"]
