from src.adapters.fhir_adapter import FHIRPatientAdapter, FHIRObservationAdapter, FHIRBundleBuilder


def test_patient_adapter_from_fhir_to_fhir_roundtrip():
    """FHIR Patient → internal → FHIR roundtrip preserves key fields"""
    fhir_patient = {
        "resourceType": "Patient",
        "id": "pat-001",
        "gender": "male",
        "birthDate": "1970-03-15",
        "identifier": [{"system": "http://hospital.example.org/mrn", "value": "MRN12345"}],
    }
    internal = FHIRPatientAdapter.from_fhir(fhir_patient)
    assert internal["fhir_id"] == "pat-001"
    assert internal["gender"] == "M"
    assert internal["birth_year"] == 1970
    assert internal["identifier"] == "MRN12345"

    # Roundtrip back to FHIR
    fhir_out = FHIRPatientAdapter.to_fhir(internal)
    assert fhir_out["resourceType"] == "Patient"
    assert fhir_out["id"] == "pat-001"
    assert fhir_out["gender"] == "M"
    assert "1970" in fhir_out["birthDate"]


def test_observation_adapter_from_fhir():
    """FHIR Observation → internal lab result"""
    fhir_obs = {
        "resourceType": "Observation",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": "2339-0", "display": "Glucose"}]
        },
        "valueQuantity": {"value": 7.8, "unit": "mmol/L"},
        "effectiveDateTime": "2026-05-30T07:00:00Z",
    }
    result = FHIRObservationAdapter.from_fhir(fhir_obs)
    assert result["code"] == "2339-0"
    assert result["value"] == 7.8
    assert result["unit"] == "mmol/L"
    assert result["effective_date"] == "2026-05-30T07:00:00Z"
