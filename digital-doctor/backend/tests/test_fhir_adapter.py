import pytest
from src.adapters.fhir_adapter import (
    FHIRPatientAdapter,
    FHIRObservationAdapter,
    FHIRBundleBuilder,
)


def test_fhir_patient_from_fhir():
    fhir = {
        "resourceType": "Patient",
        "id": "pat-001",
        "gender": "male",
        "birthDate": "1970-03-15",
        "identifier": [{"value": "MRN-12345"}],
    }
    result = FHIRPatientAdapter.from_fhir(fhir)
    assert result["fhir_id"] == "pat-001"
    assert result["gender"] == "M"
    assert result["birth_year"] == 1970
    assert result["identifier"] == "MRN-12345"


def test_fhir_patient_to_fhir():
    patient = {"fhir_id": "pat-001", "gender": "M", "birth_year": 1970}
    result = FHIRPatientAdapter.to_fhir(patient)
    assert result["resourceType"] == "Patient"
    assert result["id"] == "pat-001"
    assert result["gender"] == "M"


def test_fhir_observation_from_fhir():
    fhir = {
        "resourceType": "Observation",
        "code": {"coding": [{"code": "2345-7", "display": "Glucose"}]},
        "valueQuantity": {"value": 6.5, "unit": "mmol/L"},
        "effectiveDateTime": "2026-05-30T07:00:00Z",
    }
    result = FHIRObservationAdapter.from_fhir(fhir)
    assert result["code"] == "2345-7"
    assert result["value"] == 6.5
    assert result["unit"] == "mmol/L"


def test_fhir_bundle_builder():
    resources = [{"id": "1", "name": "test"}]
    bundle = FHIRBundleBuilder.build_search_bundle(resources, "Patient", 1)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["total"] == 1
    assert len(bundle["entry"]) == 1
