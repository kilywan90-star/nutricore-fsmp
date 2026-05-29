import pytest
from src.adapters.mock_his import (
    generate_mock_patient_panel,
    generate_mock_glucose_history,
    generate_mock_lab_orders,
)


def test_generate_patients_correct_count():
    """Patient panel generates the correct number of patients."""
    patients = generate_mock_patient_panel(count=10)
    assert len(patients) == 10
    # Also check generated patients have expected structure
    for p in patients:
        assert "fhir_id" in p
        assert "gender" in p
        assert p["gender"] in ("M", "F")
        assert "birth_year" in p
        assert "diabetes_type" in p
        assert "treatment_stage" in p


def test_glucose_history_expected_length():
    """Glucose history generates records with daily patterns over the period."""
    records = generate_mock_glucose_history("test-patient-id", days=30)
    # 30 days, ~70% compliance, fasting + some postprandial
    assert len(records) > 10  # at least some records
    assert len(records) <= 120  # at most 30 * 4

    # Check record structure
    for r in records:
        assert "value_mmol_l" in r
        assert "measure_type" in r
        assert r["measure_type"] in ("fasting", "postprandial")
        assert "recorded_at" in r
        assert r["patient_id"] == "test-patient-id"

    # Check ordering: descending by recorded_at
    for i in range(len(records) - 1):
        assert records[i]["recorded_at"] >= records[i + 1]["recorded_at"]


def test_patients_have_realistic_distributions():
    """Generated patients match T2DM epidemiology distributions."""
    patients = generate_mock_patient_panel(count=50)

    # Age: should span reasonable range (18-85)
    ages = [p["age"] for p in patients]
    assert max(ages) <= 85
    assert min(ages) >= 18

    # Peak at 45-65 (at least 30% should be in this range)
    middle_aged = sum(1 for a in ages if 45 <= a <= 65)
    assert middle_aged >= 15  # at least 30%

    # Gender: rough 55/45 split, allow variation
    male_count = sum(1 for p in patients if p["gender"] == "M")
    female_count = sum(1 for p in patients if p["gender"] == "F")
    assert male_count + female_count == 50
    # Should be roughly balanced, but allow variation in small samples
    assert 15 <= male_count <= 40
    assert 15 <= female_count <= 40

    # Treatment stages should all be present
    stages = {p["treatment_stage"] for p in patients}
    expected_stages = {"new_diagnosis", "oral_medication", "insulin", "combination"}
    assert stages == expected_stages


def test_generate_mock_lab_orders():
    """Lab orders match guideline recommendations."""
    orders = generate_mock_lab_orders("test-patient-id")
    assert len(orders) > 0

    # Check structure
    for o in orders:
        assert "order_type" in o
        assert "order_name" in o
        assert "order_date" in o
        assert "status" in o

    # Should include HbA1c orders
    hba1c_orders = [o for o in orders if o["order_type"] == "hba1c_only"]
    assert len(hba1c_orders) >= 2

    # Should include lipid panel
    lipid_orders = [o for o in orders if o["order_type"] == "lipid_panel"]
    assert len(lipid_orders) >= 1

    # Orders sorted by date descending
    for i in range(len(orders) - 1):
        assert orders[i]["order_date"] >= orders[i + 1]["order_date"]


def test_deterministic_generation():
    """Same seed should produce identical results."""
    panel1 = generate_mock_patient_panel(count=5)
    panel2 = generate_mock_patient_panel(count=5)
    for p1, p2 in zip(panel1, panel2):
        assert p1["name_hash"] == p2["name_hash"]
        assert p1["birth_year"] == p2["birth_year"]
        assert p1["gender"] == p2["gender"]
