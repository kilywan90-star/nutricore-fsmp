import pytest
from src.services.drug_checker import DrugChecker


@pytest.fixture
def checker():
    return DrugChecker()


def test_penicillin_allergy_blocks_amoxicillin(checker):
    """Penicillin allergy should block amoxicillin (same class)."""
    result = checker.check_allergy_cross_reference(
        ["Amoxicillin"], ["青霉素"]
    )
    assert len(result) >= 1
    assert result[0]["severity"] == "blocked"
    assert "青霉素" in result[0]["message"] or "penicillin" in result[0]["message"].lower()


def test_no_allergy_passes(checker):
    """No patient allergies should return empty result."""
    result = checker.check_allergy_cross_reference(
        ["Metformin", "Aspirin"], []
    )
    assert result == []


def test_multiple_allergies_multiple_drugs(checker):
    """Multiple allergies cross-checked with multiple drugs."""
    result = checker.check_allergy_cross_reference(
        ["Amoxicillin", "Metformin", "Sulfamethoxazole"],
        ["青霉素", "磺胺"]
    )
    assert len(result) >= 2
    blocked_drugs = [r["drug"] for r in result]
    assert "Amoxicillin" in blocked_drugs or any(
        "amoxicillin" in b.lower() for b in blocked_drugs
    )


def test_empty_list_returns_empty(checker):
    """Empty medication list returns empty results."""
    result = checker.check_allergy_cross_reference(
        [], ["青霉素"]
    )
    assert result == []
