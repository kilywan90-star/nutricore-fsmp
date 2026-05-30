import pytest
from src.services.drug_checker import DrugChecker
from src.services.prescription_review import PrescriptionReviewer


@pytest.fixture
def reviewer():
    checker = DrugChecker()
    return PrescriptionReviewer(checker)


def test_review_safe_prescription(reviewer):
    """Metformin monotherapy for newly diagnosed T2DM with normal renal function."""
    result = reviewer.review_prescription(
        diagnosis="type2_diabetes_newly_diagnosed",
        medications=[
            {"name": "Metformin", "dose": "500mg", "frequency": "bid"},
        ],
        patient_data={"conditions": []},
        lab_results={"egfr": 85, "alt": 20, "hba1c": 7.5},
    )
    assert result["overall_rating"] in ("safe", "caution")
    # Metformin alone should be reasonably safe
    assert result["overall_rating"] != "unsafe"


def test_review_caution_with_interaction(reviewer):
    """Sulfonylurea + insulin combination should trigger caution."""
    result = reviewer.review_prescription(
        diagnosis="type2_diabetes",
        medications=[
            {"name": "Glimepiride", "dose": "4mg", "frequency": "qd"},
            {"name": "Insulin Glargine", "dose": "20U", "frequency": "qd"},
        ],
        patient_data={"conditions": []},
        lab_results={"egfr": 70, "alt": 15, "hba1c": 8.0},
    )
    assert result["overall_rating"] in ("caution", "unsafe")
    # Should have interaction and/or concordance issues
    assert len(result["issues"]) > 0


def test_review_unsafe_with_contraindication(reviewer):
    """Rosiglitazone + insulin is contraindicated per guidelines."""
    result = reviewer.review_prescription(
        diagnosis="type2_diabetes",
        medications=[
            {"name": "Rosiglitazone", "dose": "4mg", "frequency": "qd"},
            {"name": "Insulin Glargine", "dose": "20U", "frequency": "qd"},
        ],
        patient_data={"conditions": []},
        lab_results={"egfr": 75, "alt": 18, "hba1c": 9.5},
    )
    assert result["overall_rating"] == "unsafe"
    # Must have at least one contraindicated-level issue
    contras = [i for i in result["issues"] if i["severity"] == "contraindicated"]
    assert len(contras) >= 1


def test_review_renal_contraindication(reviewer):
    """Metformin prescribed with eGFR < 30 should trigger renal concerns."""
    result = reviewer.review_prescription(
        diagnosis="type2_diabetes",
        medications=[
            {"name": "Metformin", "dose": "1000mg", "frequency": "bid"},
        ],
        patient_data={"conditions": []},
        lab_results={"egfr": 25, "alt": 18, "hba1c": 7.5},
    )
    # Should flag renal dosing issue (metformin contraindicated at eGFR < 30)
    renal_issues = [i for i in result["issues"] if i["category"] == "renal_dosing"]
    assert len(renal_issues) >= 1


def test_review_high_hba1c_insulin_recommendation(reviewer):
    """HbA1c >= 9% without insulin should trigger guideline recommendation."""
    result = reviewer.review_prescription(
        diagnosis="type2_diabetes",
        medications=[
            {"name": "Metformin", "dose": "1000mg", "frequency": "bid"},
            {"name": "Sitagliptin", "dose": "100mg", "frequency": "qd"},
        ],
        patient_data={"conditions": []},
        lab_results={"egfr": 80, "alt": 22, "hba1c": 9.5},
    )
    # Should recommend considering insulin
    guideline_issues = [i for i in result["issues"] if i["category"] == "guideline_concordance"]
    insulin_recs = [i for i in guideline_issues if "胰岛素" in i.get("recommendation", "")]
    assert len(insulin_recs) >= 1
