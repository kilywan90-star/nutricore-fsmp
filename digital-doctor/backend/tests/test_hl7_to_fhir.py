"""Tests for HL7 v2 to FHIR R4 mapper."""

import pytest
from src.adapters.hl7_parser import HL7Parser
from src.adapters.hl7_to_fhir import HL7ToFHIRMapper


# ---------------------------------------------------------------------------
# Test 1: ADT → FHIRPatient mapping
# ---------------------------------------------------------------------------

def test_adt_to_fhir_patient():
    """ADT parsed data should map to a FHIRPatient correctly."""
    adt_data = {
        "patient_id": "12345",
        "name": "张三",
        "gender": "male",
        "birth_date": "19800115",
        "birth_year": 1980,
        "admission_date": "20260530080000",
        "department": "General Hospital",
        "attending_doctor": "李医生",
    }

    patient = HL7ToFHIRMapper.adt_to_fhir_patient(adt_data)
    assert patient.id == "12345"
    assert patient.name == "张三"
    assert patient.gender == "male"
    assert patient.birth_date == "19800115"
    assert patient.identifier == "12345"

    fhir_json = patient.to_fhir_json()
    assert fhir_json["resourceType"] == "Patient"
    assert fhir_json["id"] == "12345"
    assert fhir_json["gender"] == "male"


# ---------------------------------------------------------------------------
# Test 2: ORU → Observation mapping
# ---------------------------------------------------------------------------

def test_oru_to_fhir_observations():
    """ORU parsed data should map to FHIR Observation dicts correctly."""
    oru_data = {
        "patient_id": "12345",
        "order_number": "LAB001",
        "observations": [
            {
                "test_code": "2345-7",
                "test_name": "Glucose",
                "result_value": 8.5,
                "unit": "mmol/L",
                "reference_range": "3.9-6.1",
                "abnormal_flag": "H",
                "result_date": "20260530084500",
            },
            {
                "test_code": "4548-4",
                "test_name": "HbA1c",
                "result_value": 7.2,
                "unit": "%",
                "reference_range": "4.0-6.0",
                "abnormal_flag": "H",
                "result_date": "20260530084500",
            },
        ],
    }

    observations = HL7ToFHIRMapper.oru_to_fhir_observations(oru_data)
    assert len(observations) == 2

    obs1 = observations[0]
    assert obs1["resourceType"] == "Observation"
    assert obs1["status"] == "final"
    assert obs1["code"]["coding"][0]["code"] == "2345-7"
    assert obs1["code"]["coding"][0]["display"] == "Glucose"
    assert obs1["valueQuantity"]["value"] == 8.5
    assert obs1["valueQuantity"]["unit"] == "mmol/L"
    assert obs1["subject"]["reference"] == "Patient/12345"
    assert obs1["referenceRange"][0]["text"] == "3.9-6.1"
    assert obs1["interpretation"][0]["coding"][0]["code"] == "H"

    obs2 = observations[1]
    assert obs2["code"]["coding"][0]["code"] == "4548-4"
    assert obs2["valueQuantity"]["value"] == 7.2
    assert obs2["valueQuantity"]["unit"] == "%"


# ---------------------------------------------------------------------------
# Test 3: ORM → MedicationRequest mapping
# ---------------------------------------------------------------------------

def test_orm_to_fhir_medication_requests():
    """ORM parsed data should map to FHIR MedicationRequest dicts correctly."""
    orm_data = {
        "patient_id": "12345",
        "medication_orders": [
            {
                "order_number": "ORD001",
                "drug_code": "0043-0488-10",
                "drug_name": "二甲双胍",
                "dose": "500 mg",
                "route": "口服",
                "frequency": "bid",
                "start_date": "20260530",
                "ordering_doctor": "李医生",
            },
            {
                "order_number": "ORD002",
                "drug_code": "0002-8500",
                "drug_name": "胰岛素",
                "dose": "10 IU",
                "route": "皮下注射",
                "frequency": "qd",
                "start_date": "20260530",
                "ordering_doctor": "李医生",
            },
        ],
    }

    requests = HL7ToFHIRMapper.orm_to_fhir_medication_requests(orm_data)
    assert len(requests) == 2

    req1 = requests[0]
    assert req1["resourceType"] == "MedicationRequest"
    assert req1["id"] == "ORD001"
    assert req1["status"] == "active"
    assert req1["intent"] == "order"
    assert req1["medicationCodeableConcept"]["coding"][0]["code"] == "0043-0488-10"
    assert req1["medicationCodeableConcept"]["coding"][0]["display"] == "二甲双胍"
    assert req1["subject"]["reference"] == "Patient/12345"
    assert req1["dosageInstruction"][0]["text"] == "500 mg"
    assert req1["dosageInstruction"][0]["route"]["coding"][0]["display"] == "口服"
    assert req1["requester"]["reference"] == "Practitioner/李医生"

    req2 = requests[1]
    assert req2["id"] == "ORD002"
    assert req2["medicationCodeableConcept"]["coding"][0]["display"] == "胰岛素"
    assert req2["requester"]["reference"] == "Practitioner/李医生"
