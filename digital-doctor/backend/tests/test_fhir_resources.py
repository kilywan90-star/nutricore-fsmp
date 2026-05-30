"""Tests for FHIR R4 resource models — roundtrip, parsing, and bundle operations."""

import pytest
from src.adapters.fhir_resources import (
    FHIRAllergyIntolerance,
    FHIRCarePlan,
    FHIRCondition,
    FHIRDiagnosticReport,
    FHIRDocumentReference,
    FHIRImmunization,
    FHIRMedicationRequest,
    FHIRPatient,
    FHIRProcedure,
)
from src.adapters.fhir_bundle import parse_fhir_bundle, build_fhir_bundle


# ---------------------------------------------------------------------------
# Test 1: FHIRPatient roundtrip (from_fhir_resource → to_fhir_json)
# ---------------------------------------------------------------------------

def test_patient_roundtrip():
    """FHIRPatient should correctly roundtrip from FHIR JSON and back."""
    fhir_json = {
        "resourceType": "Patient",
        "id": "pat-001",
        "gender": "female",
        "birthDate": "1976-05-20",
        "identifier": [
            {"system": "urn:oid:2.16.156.10011.1.1", "value": "MRN-12345"}
        ],
        "name": [
            {"use": "official", "family": "Zhang", "given": ["San"]}
        ],
    }

    patient = FHIRPatient.from_fhir_resource(fhir_json)
    assert patient.id == "pat-001"
    assert patient.gender == "female"
    assert patient.birth_date == "1976-05-20"
    assert patient.identifier == "MRN-12345"
    assert "Zhang" in patient.name

    out = patient.to_fhir_json()
    assert out["resourceType"] == "Patient"
    assert out["id"] == "pat-001"
    assert out["gender"] == "female"
    assert out["birthDate"] == "1976-05-20"
    assert out["identifier"][0]["value"] == "MRN-12345"


# ---------------------------------------------------------------------------
# Test 2: FHIRCondition from/to FHIR
# ---------------------------------------------------------------------------

def test_condition_from_and_to_fhir():
    """FHIRCondition should parse and serialize correctly."""
    fhir_json = {
        "resourceType": "Condition",
        "id": "cond-001",
        "clinicalStatus": {
            "coding": [
                {"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}
            ]
        },
        "verificationStatus": {
            "coding": [
                {"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}
            ]
        },
        "code": {
            "coding": [
                {"system": "http://snomed.info/sct", "code": "44054006", "display": "Type 2 diabetes mellitus"}
            ],
            "text": "2型糖尿病",
        },
        "subject": {"reference": "Patient/fh-pat-0001"},
        "onsetDateTime": "2018-05-20",
        "recordedDate": "2026-05-30T08:00:00Z",
        "recorder": {"reference": "Practitioner/doc-001"},
    }

    condition = FHIRCondition.from_fhir_resource(fhir_json)
    assert condition.id == "cond-001"
    assert condition.patient_id == "fh-pat-0001"
    assert condition.code == "44054006"
    assert condition.code_system == "http://snomed.info/sct"
    assert condition.code_display == "Type 2 diabetes mellitus"
    assert condition.clinical_status == "active"
    assert condition.verification_status == "confirmed"
    assert condition.onset_date == "2018-05-20"
    assert condition.recorder == "doc-001"

    out = condition.to_fhir_json()
    assert out["resourceType"] == "Condition"
    assert out["id"] == "cond-001"
    assert out["code"]["coding"][0]["code"] == "44054006"
    assert out["subject"]["reference"] == "Patient/fh-pat-0001"
    assert out["clinicalStatus"]["coding"][0]["code"] == "active"


# ---------------------------------------------------------------------------
# Test 3: Observation with LOINC codes (via FHIRObservationAdapter for coverage)
# ---------------------------------------------------------------------------

def test_observation_with_loinc_codes():
    """Observation adapter should correctly extract LOINC-coded lab results."""
    from src.adapters.fhir_adapter import FHIRObservationAdapter

    fhir = {
        "resourceType": "Observation",
        "id": "obs-glc-001",
        "code": {
            "coding": [
                {"system": "http://loinc.org", "code": "2345-7", "display": "Glucose [Moles/volume] in Blood"}
            ],
            "text": "空腹血糖",
        },
        "valueQuantity": {"value": 6.5, "unit": "mmol/L", "system": "http://unitsofmeasure.org", "code": "mmol/L"},
        "effectiveDateTime": "2026-05-30T06:30:00Z",
    }

    result = FHIRObservationAdapter.from_fhir(fhir)
    assert result["code"] == "2345-7"
    assert result["value"] == 6.5
    assert result["unit"] == "mmol/L"
    assert result["effective_date"] == "2026-05-30T06:30:00Z"


# ---------------------------------------------------------------------------
# Test 4: Bundle parsing
# ---------------------------------------------------------------------------

def test_parse_fhir_bundle():
    """parse_fhir_bundle should categorize resources by resourceType."""
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "total": 5,
        "entry": [
            {
                "fullUrl": "urn:uuid:p1",
                "resource": {
                    "resourceType": "Patient",
                    "id": "p1",
                    "gender": "male",
                },
            },
            {
                "fullUrl": "urn:uuid:p2",
                "resource": {
                    "resourceType": "Patient",
                    "id": "p2",
                    "gender": "female",
                },
            },
            {
                "fullUrl": "urn:uuid:o1",
                "resource": {
                    "resourceType": "Observation",
                    "id": "o1",
                    "code": {"text": "Glucose"},
                },
            },
            {
                "fullUrl": "urn:uuid:c1",
                "resource": {
                    "resourceType": "Condition",
                    "id": "c1",
                    "code": {"text": "Diabetes"},
                },
            },
            {
                "fullUrl": "urn:uuid:o2",
                "resource": {
                    "resourceType": "Observation",
                    "id": "o2",
                    "code": {"text": "HbA1c"},
                },
            },
        ],
    }

    categorized = parse_fhir_bundle(bundle)
    assert "Patient" in categorized
    assert "Observation" in categorized
    assert "Condition" in categorized
    assert len(categorized["Patient"]) == 2
    assert len(categorized["Observation"]) == 2
    assert len(categorized["Condition"]) == 1
    assert categorized["Patient"][0]["id"] == "p1"
    assert categorized["Condition"][0]["id"] == "c1"


# ---------------------------------------------------------------------------
# Test 5: Bundle building
# ---------------------------------------------------------------------------

def test_build_fhir_bundle():
    """build_fhir_bundle should produce a valid searchset Bundle."""
    resources = [
        {"id": "pat-001", "name": [{"family": "Li"}]},
        {"id": "pat-002", "name": [{"family": "Wang"}]},
    ]

    bundle = build_fhir_bundle(resources, "Patient", 42)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 42
    assert len(bundle["entry"]) == 2
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"
    assert bundle["entry"][0]["resource"]["id"] == "pat-001"
    assert bundle["entry"][0]["fullUrl"] == "urn:uuid:pat-001"
