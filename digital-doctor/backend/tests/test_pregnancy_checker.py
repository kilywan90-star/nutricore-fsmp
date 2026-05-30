import pytest
from src.services.pregnancy_checker import (
    check_pregnancy_safety,
    PregnancyStatus,
)


def test_category_d_drug_blocked_for_pregnancy():
    """Category D drug (Lisinopril) should be blocked for pregnant patient."""
    result = check_pregnancy_safety(
        ["Lisinopril"],
        PregnancyStatus.PREGNANT,
        patient_age=30,
        patient_gender="F",
    )
    assert len(result) >= 1
    blocked = [r for r in result if r.severity == "blocked"]
    assert len(blocked) >= 1
    assert blocked[0].category == "D"


def test_category_c_drug_warning_for_pregnancy():
    """Category C drug (Sitagliptin) should give warning for pregnant patient."""
    result = check_pregnancy_safety(
        ["Sitagliptin"],
        PregnancyStatus.PREGNANT,
        patient_age=28,
        patient_gender="F",
    )
    assert len(result) >= 1
    warnings = [r for r in result if r.severity == "warning"]
    assert len(warnings) >= 1
    assert warnings[0].category == "C"


def test_not_pregnant_no_restrictions():
    """Not pregnant patient should have no pregnancy-related restrictions."""
    result = check_pregnancy_safety(
        ["Lisinopril", "Isotretinoin", "Warfarin"],
        PregnancyStatus.NOT_PREGNANT,
        patient_age=35,
        patient_gender="F",
    )
    assert result == []


def test_unknown_status_prompts_if_female_childbearing():
    """Unknown pregnancy status + female 15-50 should prompt confirmation."""
    result = check_pregnancy_safety(
        ["Metformin"],
        PregnancyStatus.UNKNOWN,
        patient_age=30,
        patient_gender="F",
    )
    assert len(result) == 1
    assert result[0].severity == "info"
    assert "妊娠" in result[0].message
    assert "确认" in result[0].recommendation or "评估" in result[0].recommendation
