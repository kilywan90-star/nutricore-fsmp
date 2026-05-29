import pytest
from src.adapters.fhir_testdata import (
    load_sample_patients,
    load_sample_observations,
    load_sample_bundle,
)


def test_sample_patients_have_required_fhir_fields():
    """Sample FHIR patients have all required R4 Patient resource fields."""
    patients = load_sample_patients()
    assert len(patients) == 10

    required_fields = ["resourceType", "id", "gender", "birthDate"]
    for p in patients:
        assert p["resourceType"] == "Patient"
        for field in required_fields:
            assert field in p, f"Missing '{field}' in patient {p.get('id')}"

        # Identifier should exist
        assert "identifier" in p
        assert len(p["identifier"]) > 0
        assert "value" in p["identifier"][0]

        # Name should follow FHIR HumanName format
        assert "name" in p
        assert len(p["name"]) > 0
        assert "family" in p["name"][0]
        assert "given" in p["name"][0]

        # Gender should be a valid FHIR AdministrativeGender
        assert p["gender"] in ("male", "female", "other", "unknown")

        # Extension for diabetes-specific fields
        assert "extension" in p
        extensions = p["extension"]
        assert any(ext["url"].endswith("diabetes-type") for ext in extensions)
        assert any(ext["url"].endswith("hba1c-target") for ext in extensions)


def test_sample_observations_have_required_fhir_fields():
    """Sample FHIR observations have valid structure."""
    observations = load_sample_observations()
    assert len(observations) > 0

    for obs in observations:
        assert obs["resourceType"] == "Observation"
        assert "id" in obs
        assert obs["status"] == "final"
        assert "code" in obs
        assert "subject" in obs
        assert "reference" in obs["subject"]
        assert obs["subject"]["reference"].startswith("Patient/")

        # Should have a value
        assert "valueQuantity" in obs
        assert "value" in obs["valueQuantity"]
        assert "unit" in obs["valueQuantity"]

    # Verify we have the expected observation types
    loinc_codes = set()
    for obs in observations:
        for coding in obs["code"].get("coding", []):
            loinc_codes.add(coding.get("code", ""))

    # Check key LOINC codes are present
    assert "2345-7" in loinc_codes  # Glucose
    assert "4548-4" in loinc_codes  # HbA1c
    assert "2093-3" in loinc_codes  # Cholesterol
    assert "2160-0" in loinc_codes  # Creatinine


def test_sample_observations_count():
    """Sample observations should have at least 50 entries."""
    observations = load_sample_observations()
    assert len(observations) >= 50


def test_bundle_structure_is_valid():
    """FHIR Bundle has valid structure for bulk import testing."""
    bundle = load_sample_bundle()

    # Bundle resource type
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "transaction"
    assert "id" in bundle
    assert "total" in bundle

    # All entries must have fullUrl, resource, and request
    assert "entry" in bundle
    assert len(bundle["entry"]) == bundle["total"]
    assert len(bundle["entry"]) > 10  # Should have both patients and observations

    for entry in bundle["entry"]:
        assert "fullUrl" in entry
        assert "resource" in entry
        assert "request" in entry
        assert "method" in entry["request"]
        assert entry["request"]["method"] in ("PUT", "POST")
        assert "url" in entry["request"]

    # Verify bundle contains both Patient and Observation resources
    resource_types = {entry["resource"]["resourceType"] for entry in bundle["entry"]}
    assert "Patient" in resource_types
    assert "Observation" in resource_types
