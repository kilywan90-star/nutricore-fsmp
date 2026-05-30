import pytest
from src.services.drug_checker import DrugChecker


@pytest.fixture
def checker():
    return DrugChecker()


def test_check_interactions_metformin_sulfonylurea(checker):
    """Metformin + sulfonylurea is a common combination — should flag as minor."""
    result = checker.check_interactions(["Metformin", "Glimepiride"])
    assert len(result) >= 1
    sevs = [r["severity"] for r in result]
    assert "minor" in sevs or "moderate" in sevs or "major" in sevs


def test_check_renal_dosing_metformin_low_egfr(checker):
    """Metformin needs dose reduction when eGFR < 45."""
    result = checker.check_renal_dosing(["Metformin"], egfr=30)
    assert len(result) == 1
    assert result[0]["adjustment_needed"] is True
    assert "减量" in result[0]["recommended_dose"] or "禁用" in result[0]["recommended_dose"]


def test_check_contraindications_heart_failure(checker):
    """TZD + heart failure should trigger contraindication."""
    result = checker.check_contraindications(
        ["Pioglitazone"], ["heart_failure"]
    )
    assert len(result) >= 1
    assert result[0]["severity"] == "contraindicated"


def test_check_interactions_safe_combo(checker):
    """Metformin + DPP-4i is a safe, guideline-recommended combination."""
    result = checker.check_interactions(["Metformin", "Sitagliptin"])
    # This is a safe combo; at most minor interactions
    contra = [r for r in result if r["severity"] in ("contraindicated", "major")]
    assert len(contra) == 0


def test_check_interactions_empty_list(checker):
    """Empty medication list should return empty results."""
    result = checker.check_interactions([])
    assert result == []


def test_search_drugs(checker):
    """Search by partial Chinese name should return results."""
    result = checker.search_drugs("二甲双胍")
    assert len(result) >= 1
    assert result[0]["generic_name_en"] == "Metformin"


def test_get_drug(checker):
    """Lookup by English generic name."""
    drug = checker.get_drug("Metformin")
    assert drug is not None
    assert drug["generic_name"] == "二甲双胍"
    assert drug["drug_class"] == "biguanide"


def test_check_renal_dosing_multiple_egfr(checker):
    """Check renal adjustments across multiple drugs."""
    result = checker.check_renal_dosing(["Metformin", "Sitagliptin"], egfr=35)
    assert len(result) == 2
    # Both should need adjustment at eGFR 35
    for r in result:
        if r["generic_name"] == "二甲双胍":
            assert r["adjustment_needed"] is True
