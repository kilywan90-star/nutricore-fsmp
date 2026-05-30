"""Tests for EMR adapter layer: all 8 adapters, factory, and NoOp behavior."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.emr_base import (
    AllergyIntolerance,
    Condition,
    Encounter,
    FHIRPatient,
    LiverFunction,
    MedicationRequest,
    Observation,
    PregnancyStatus,
    RenalFunction,
)
from src.adapters.emr_factory import get_emr_adapter, reset_emr_adapter
from src.adapters.vendors.bsoft import BsoftAdapter
from src.adapters.vendors.fhir_standard import FHIRStandardAdapter
from src.adapters.vendors.neusoft import NeusoftAdapter
from src.adapters.vendors.noop import NoOpAdapter
from src.adapters.vendors.winning import WinningAdapter
from src.adapters.vendors.wonders import WondersAdapter
from src.adapters.vendors.xintong import XintongAdapter
from src.adapters.vendors.zuobiao import ZuobiaoAdapter


# ── Shared test data ──────────────────────────────────────────────────────────

FAKE_PATIENT_FHIR = {
    "id": "pat-001",
    "identifier": [{"value": "PID-12345"}],
    "name": [{"text": "张三"}],
    "gender": "male",
    "birthDate": "1965-03-15",
    "telecom": [{"system": "phone", "value": "13800138000"}],
    "address": [{"line": ["北京市朝阳区"], "city": "北京"}],
}

FAKE_ALLERGY_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [{
        "resource": {
            "resourceType": "AllergyIntolerance",
            "id": "allergy-001",
            "patient": {"reference": "Patient/pat-001"},
            "code": {"coding": [{"code": "J01CF01", "display": "青霉素"}]},
            "category": ["medication"],
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "onsetDateTime": "2024-01-15",
            "recordedDate": "2024-01-16",
        },
    }],
}

FAKE_OBS_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [{
        "resource": {
            "resourceType": "Observation",
            "id": "obs-001",
            "code": {"coding": [{"code": "4548-4", "display": "HbA1c"}]},
            "valueQuantity": {"value": 7.2, "unit": "%"},
            "effectiveDateTime": "2025-05-20",
            "referenceRange": [{"low": {"value": 4.0}, "high": {"value": 6.0}}],
            "status": "final",
        },
    }],
}

FAKE_MED_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [{
        "resource": {
            "resourceType": "MedicationRequest",
            "id": "med-001",
            "medicationReference": {"display": "二甲双胍 500mg"},
            "dosageInstruction": [{
                "doseQuantity": {"value": 500, "unit": "mg"},
                "timing": {"code": {"coding": [{"code": "bid"}]}},
                "route": {"coding": [{"code": "po"}]},
            }],
            "authoredOn": "2025-01-10",
            "status": "active",
        },
    }],
}

FAKE_CONDITION_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [{
        "resource": {
            "resourceType": "Condition",
            "id": "cond-001",
            "code": {"coding": [{"code": "E11.9", "display": "2型糖尿病"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "onsetDateTime": "2023-06-01",
        },
    }],
}

FAKE_ENCOUNTER_FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [{
        "resource": {
            "resourceType": "Encounter",
            "id": "enc-001",
            "class": {"code": "outpatient"},
            "period": {"start": "2025-05-01"},
            "serviceType": [{"coding": [{"display": "内分泌科"}]}],
            "participant": [{"individual": {"display": "李医生"}}],
            "reasonCode": [{"text": "血糖控制评估"}],
        },
    }],
}

SOAP_HEADER = (
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
    '<soap:Body>'
)
SOAP_FOOTER = "</soap:Body></soap:Envelope>"


def _soap_envelope(xml_body: str) -> str:
    return f"{SOAP_HEADER}{xml_body}{SOAP_FOOTER}"


def _mock_soap_response(text: str):
    m = AsyncMock()
    m.text = text
    m.raise_for_status = lambda: None
    return m


def _mock_json_response(data: dict):
    m = AsyncMock()
    m.json = lambda: data
    m.raise_for_status = lambda: None
    return m


# ── Factory tests ────────────────────────────────────────────────────────────

class TestAdapterFactory:
    """Factory returns correct adapter type based on settings."""

    def test_factory_returns_noop_by_default(self, monkeypatch):
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_VENDOR", "noop")
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_ENDPOINT", "")
        reset_emr_adapter()
        adapter = get_emr_adapter()
        assert isinstance(adapter, NoOpAdapter)

    def test_factory_returns_fhir_adapter(self, monkeypatch):
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_VENDOR", "fhir")
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_ENDPOINT", "http://fhir-server/fhir")
        reset_emr_adapter()
        adapter = get_emr_adapter()
        assert isinstance(adapter, FHIRStandardAdapter)

    def test_factory_caches_adapter(self, monkeypatch):
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_VENDOR", "noop")
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_ENDPOINT", "")
        reset_emr_adapter()
        a1 = get_emr_adapter()
        a2 = get_emr_adapter()
        assert a1 is a2

    @pytest.mark.parametrize("vendor,expected_type", [
        ("neusoft", NeusoftAdapter),
        ("winning", WinningAdapter),
        ("bsoft", BsoftAdapter),
        ("wonders", WondersAdapter),
        ("xintong", XintongAdapter),
        ("zuobiao", ZuobiaoAdapter),
    ])
    def test_factory_returns_correct_type(self, monkeypatch, vendor, expected_type):
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_VENDOR", vendor)
        monkeypatch.setattr("src.adapters.emr_factory.settings.EMR_ENDPOINT", "http://test/")
        reset_emr_adapter()
        adapter = get_emr_adapter()
        assert isinstance(adapter, expected_type)


# ── NoOp adapter tests ───────────────────────────────────────────────────────

class TestNoOpAdapter:
    """NoOp adapter returns empty/None for all methods."""

    def test_get_patient_returns_minimal(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert isinstance(result, FHIRPatient)
        assert result.id == "pat-001"
        assert result.name == ""

    def test_get_allergies_returns_empty(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_allergies("pat-001"))
        assert result == []

    def test_get_lab_results_returns_empty(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_lab_results("pat-001", date.today()))
        assert result == []

    def test_get_medications_returns_empty(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_medications("pat-001"))
        assert result == []

    def test_get_diagnoses_returns_empty(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_diagnoses("pat-001"))
        assert result == []

    def test_get_pregnancy_status_returns_none(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_pregnancy_status("pat-001"))
        assert result is None

    def test_get_liver_function_returns_none(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_liver_function("pat-001"))
        assert result is None

    def test_get_renal_function_returns_none(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_renal_function("pat-001"))
        assert result is None

    def test_get_encounters_returns_empty(self):
        adapter = NoOpAdapter()
        result = asyncio.run(adapter.get_encounters("pat-001", date.today()))
        assert result == []


# ── FHIR Standard adapter tests ──────────────────────────────────────────────

class TestFHIRStandardAdapter:
    """FHIR Standard adapter maps FHIR resources correctly."""

    def test_get_patient_maps_fields(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_get", return_value=FAKE_PATIENT_FHIR):
            result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.id == "pat-001"
        assert result.name == "张三"
        assert result.gender == "male"
        assert result.birth_date == "1965-03-15"
        assert result.identifier == "PID-12345"
        assert result.phone == "13800138000"

    def test_get_allergies_maps_substance(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value=FAKE_ALLERGY_FHIR_BUNDLE):
            results = asyncio.run(adapter.get_allergies("pat-001"))
        assert len(results) == 1
        assert results[0].substance == "青霉素"
        assert results[0].category == "medication"

    def test_get_lab_results_maps_observation(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value=FAKE_OBS_FHIR_BUNDLE):
            results = asyncio.run(adapter.get_lab_results("pat-001", date(2025, 1, 1)))
        assert len(results) == 1
        assert results[0].code == "4548-4"
        assert results[0].name == "HbA1c"
        assert results[0].value == 7.2
        assert results[0].unit == "%"
        assert results[0].reference_range == "4.0-6.0"

    def test_get_medications_maps_request(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value=FAKE_MED_FHIR_BUNDLE):
            results = asyncio.run(adapter.get_medications("pat-001"))
        assert len(results) == 1
        assert results[0].medication_name == "二甲双胍 500mg"
        assert results[0].status == "active"

    def test_get_diagnoses_maps_condition(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value=FAKE_CONDITION_FHIR_BUNDLE):
            results = asyncio.run(adapter.get_diagnoses("pat-001"))
        assert len(results) == 1
        assert results[0].name == "2型糖尿病"
        assert results[0].code == "E11.9"

    def test_get_encounters_maps_visit(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value=FAKE_ENCOUNTER_FHIR_BUNDLE):
            results = asyncio.run(adapter.get_encounters("pat-001", date(2025, 1, 1)))
        assert len(results) == 1
        assert results[0].encounter_type == "outpatient"
        assert results[0].department == "内分泌科"

    def test_get_pregnancy_status_no_data(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value={"entry": []}):
            result = asyncio.run(adapter.get_pregnancy_status("pat-001"))
        assert result is None

    def test_get_liver_function_no_data(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value={"entry": []}):
            result = asyncio.run(adapter.get_liver_function("pat-001"))
        assert result is None

    def test_get_renal_function_no_data(self):
        adapter = FHIRStandardAdapter("http://fhir.test/fhir")
        with patch.object(adapter, "_search", return_value={"entry": []}):
            result = asyncio.run(adapter.get_renal_function("pat-001"))
        assert result is None


# ── Neusoft adapter tests ────────────────────────────────────────────────────

class TestNeusoftAdapter:
    """Neusoft SOAP/XML adapter maps responses correctly."""

    def test_get_patient_parses_soap(self):
        adapter = NeusoftAdapter("http://neusoft.test/soap")
        xml = (
            '<queryPatientByIdResponse xmlns="http://www.neusoft.com/his/cdr">'
            '<patient><patientId>PID-001</patientId><patientName>张三</patientName>'
            '<genderCode>1</genderCode><birthDate>1965-03-15</birthDate>'
            '<phoneNumber>13800138000</phoneNumber><homeAddress>北京市</homeAddress>'
            '</patient></queryPatientByIdResponse>'
        )
        adapter.client.post = AsyncMock(return_value=_mock_soap_response(_soap_envelope(xml)))
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"
        assert result.gender == "M"

    def test_get_allergies_empty_when_missing(self):
        adapter = NeusoftAdapter("http://neusoft.test/soap")
        xml = (
            '<queryAllergyByPatientResponse xmlns="http://www.neusoft.com/his/cdr">'
            '</queryAllergyByPatientResponse>'
        )
        adapter.client.post = AsyncMock(return_value=_mock_soap_response(_soap_envelope(xml)))
        results = asyncio.run(adapter.get_allergies("pat-001"))
        assert results == []

    def test_get_pregnancy_status_no_flag(self):
        adapter = NeusoftAdapter("http://neusoft.test/soap")
        xml = (
            '<queryPatientByIdResponse xmlns="http://www.neusoft.com/his/cdr">'
            '<patient><pregnancyFlag>0</pregnancyFlag></patient>'
            '</queryPatientByIdResponse>'
        )
        adapter.client.post = AsyncMock(return_value=_mock_soap_response(_soap_envelope(xml)))
        result = asyncio.run(adapter.get_pregnancy_status("pat-001"))
        assert result is None


# ── Winning adapter tests ────────────────────────────────────────────────────

class TestWinningAdapter:
    """Winning WinDHP SOAP/XML adapter maps responses correctly."""

    @staticmethod
    def _make_patient_response():
        xml = (
            '<getPatientInfoResponse xmlns="http://www.winning.com.cn/WinDHP">'
            '<patientInfo><patientCode>PID-001</patientCode><patientName>张三</patientName>'
            '<sex>1</sex><birthday>1965-03-15</birthday><mobile>13800138000</mobile>'
            '<address>北京市</address></patientInfo></getPatientInfoResponse>'
        )
        return _mock_soap_response(_soap_envelope(xml))

    def test_get_patient_parses_soap(self):
        adapter = WinningAdapter("http://winning.test/soap")
        adapter.client.post = AsyncMock(return_value=self._make_patient_response())
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"
        assert result.gender == "M"

    def test_get_patient_fallback_codetypes(self):
        """Falls back through codetype 3->2->1."""
        adapter = WinningAdapter("http://winning.test/soap")
        fail = AsyncMock()
        fail.raise_for_status = lambda: (_ for _ in ()).throw(Exception("fail"))
        adapter.client.post = AsyncMock(side_effect=[fail, fail, self._make_patient_response()])
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"

    def test_get_allergies_returns_empty_on_error(self):
        adapter = WinningAdapter("http://winning.test/soap")
        adapter.client.post = AsyncMock(side_effect=Exception("timeout"))
        results = asyncio.run(adapter.get_allergies("pat-001"))
        assert results == []


# ── Wonders adapter tests ────────────────────────────────────────────────────

class TestWondersAdapter:
    """Wonders REST adapter maps JSON responses correctly."""

    def test_get_patient_parses_json(self):
        adapter = WondersAdapter("http://wonders.test/api")
        adapter.client.get = AsyncMock(return_value=_mock_json_response({
            "patientCode": "PID-001", "patientName": "张三",
            "gender": "1", "birthDate": "1965-03-15",
            "phone": "13800138000", "address": "北京市",
        }))
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"
        assert result.gender == "M"

    def test_get_allergies_parses_list(self):
        adapter = WondersAdapter("http://wonders.test/api")
        adapter.client.get = AsyncMock(return_value=_mock_json_response({
            "allergies": [{"id": "A1", "allergen": "青霉素", "type": "medication", "level": "moderate"}],
        }))
        results = asyncio.run(adapter.get_allergies("pat-001"))
        assert len(results) == 1
        assert results[0].substance == "青霉素"

    def test_get_patient_graceful_fallback(self):
        adapter = WondersAdapter("http://wonders.test/api")
        adapter.client.get = AsyncMock(side_effect=Exception("timeout"))
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert isinstance(result, FHIRPatient)
        assert result.id == "pat-001"

    def test_get_pregnancy_status_from_patient_info(self):
        adapter = WondersAdapter("http://wonders.test/api")
        adapter.client.get = AsyncMock(return_value=_mock_json_response({
            "isPregnant": True, "gestationalWeeks": 12, "edd": "2025-12-01",
        }))
        result = asyncio.run(adapter.get_pregnancy_status("pat-001"))
        assert result is not None
        assert result.is_pregnant is True
        assert result.gestational_weeks == 12


# ── Xintong adapter tests ────────────────────────────────────────────────────

class TestXintongAdapter:
    """Xintong SOAP/XML adapter maps responses correctly."""

    @staticmethod
    def _make_patient_response():
        xml = (
            '<query_patient_infoResponse xmlns="http://www.xintong.cn/healthplatform">'
            '<patient><patientNo>PID-001</patientNo><patientName>张三</patientName>'
            '<genderCode>1</genderCode><birthDate>1965-03-15</birthDate>'
            '<mobile>13800138000</mobile><homeAddress>北京市</homeAddress>'
            '</patient></query_patient_infoResponse>'
        )
        return _mock_soap_response(_soap_envelope(xml))

    def test_get_patient_parses_soap(self):
        adapter = XintongAdapter("http://xintong.test/soap")
        adapter.client.post = AsyncMock(return_value=self._make_patient_response())
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"
        assert result.gender == "M"

    def test_get_patient_graceful_fallback(self):
        adapter = XintongAdapter("http://xintong.test/soap")
        adapter.client.post = AsyncMock(side_effect=Exception("timeout"))
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.id == "pat-001"


# ── Zuobiao adapter tests ────────────────────────────────────────────────────

class TestZuobiaoAdapter:
    """Zuobiao HealthOne SOAP/XML adapter maps responses correctly."""

    @staticmethod
    def _make_patient_response():
        xml = (
            '<getPatientInfoResponse xmlns="http://www.zuobiao.com.cn/HealthOne">'
            '<patientInfo><patientId>PID-001</patientId><patientName>张三</patientName>'
            '<gender>1</gender><birthday>1965-03-15</birthday><tel>13800138000</tel>'
            '<homeAddr>北京市</homeAddr></patientInfo></getPatientInfoResponse>'
        )
        return _mock_soap_response(_soap_envelope(xml))

    def test_get_patient_parses_soap(self):
        adapter = ZuobiaoAdapter("http://zuobiao.test/soap")
        adapter.client.post = AsyncMock(return_value=self._make_patient_response())
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"
        assert result.gender == "M"

    def test_get_patient_graceful_fallback(self):
        adapter = ZuobiaoAdapter("http://zuobiao.test/soap")
        adapter.client.post = AsyncMock(side_effect=Exception("timeout"))
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.id == "pat-001"


# ── Bsoft adapter tests ──────────────────────────────────────────────────────

class TestBsoftAdapter:
    """Bsoft Hi-HIS adapter uses FHIR primary, HL7 v2 fallback."""

    def test_get_patient_via_fhir(self):
        adapter = BsoftAdapter("http://bsoft.test")
        adapter.client.get = AsyncMock(return_value=_mock_json_response(FAKE_PATIENT_FHIR))
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "张三"
        assert result.gender == "male"

    def test_get_patient_fallback_to_hl7(self):
        """When FHIR fails, falls back to HL7 v2 ADT^A08."""
        adapter = BsoftAdapter("http://bsoft.test")
        fhir_fail = AsyncMock()
        fhir_fail.raise_for_status = lambda: (_ for _ in ()).throw(Exception("FHIR down"))
        hl7_ok = AsyncMock()
        hl7_ok.text = (
            "MSH|^~\\&|DDD|HIS|HIS|DDD|20250530120000||ADT^A08|msg1|P|2.5\r"
            "PID|1||pat-001^^^HIS||李四^^^^|^|19800101|M\r"
        )
        hl7_ok.raise_for_status = lambda: None
        adapter.client.get = AsyncMock(return_value=fhir_fail)
        adapter.client.post = AsyncMock(return_value=hl7_ok)
        result = asyncio.run(adapter.get_patient("pat-001"))
        assert result.name == "李四"
        assert result.gender == "M"


# ── Dataclass integrity tests ────────────────────────────────────────────────

class TestDataclassStructures:
    """Verify internal dataclass structures are well-formed."""

    def test_fhir_patient_defaults(self):
        p = FHIRPatient(id="test")
        assert p.id == "test"
        assert p.name == ""

    def test_allergy_intolerance_defaults(self):
        a = AllergyIntolerance(id="A1", patient_id="P1", substance="Penicillin")
        assert a.category == "medication"

    def test_observation_defaults(self):
        o = Observation(id="O1", patient_id="P1", code="4548-4")
        assert o.status == "final"
        assert o.value is None

    def test_medication_request_defaults(self):
        m = MedicationRequest(id="M1", patient_id="P1", medication_name="Metformin")
        assert m.status == "active"

    def test_condition_defaults(self):
        c = Condition(id="C1", patient_id="P1", name="Diabetes")
        assert c.category == "diagnosis"
        assert c.status == "active"

    def test_pregnancy_status_defaults(self):
        ps = PregnancyStatus(patient_id="P1")
        assert ps.is_pregnant is False
        assert ps.gestational_weeks is None

    def test_liver_function_defaults(self):
        lf = LiverFunction(patient_id="P1")
        assert lf.alt is None
        assert lf.child_pugh_class == ""

    def test_renal_function_defaults(self):
        rf = RenalFunction(patient_id="P1")
        assert rf.egfr is None
        assert rf.ckd_stage == 0

    def test_encounter_defaults(self):
        e = Encounter(id="E1", patient_id="P1")
        assert e.encounter_type == ""
