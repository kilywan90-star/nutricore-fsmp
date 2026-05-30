import pytest
from src.services.organ_assessment import (
    OrganAssessment,
    LiverFunction,
    RenalFunction,
    classify_liver,
    classify_kidney,
    get_drug_dose_adjustments,
)


def test_ckd_stage_3_metformin_adjustment():
    """CKD stage 3 (eGFR 30-59) should trigger metformin dose reduction."""
    rf = RenalFunction(egfr=35, creatinine=1.8)
    stage = classify_kidney(rf)
    assert stage in ("stage_3a", "stage_3b", "stage_3")

    adj = get_drug_dose_adjustments("Metformin", "A", stage)
    assert adj is not None
    assert adj.adjustment_needed is True
    assert "减量" in adj.adjusted_dose or "1000" in adj.adjusted_dose


def test_child_pugh_b_drug_warning():
    """Child-Pugh B liver function should trigger drug warnings."""
    lf = LiverFunction(
        alt=85, ast=90, tbil=2.5, albumin=2.9,
        inr=1.8, has_ascites=True, has_encephalopathy=False,
    )
    liver_class = classify_liver(lf)
    assert liver_class in ("B", "C")

    adj = get_drug_dose_adjustments("Pioglitazone", liver_class, "stage_1")
    assert adj is not None
    assert adj.adjustment_needed is True
    assert "禁用" in adj.adjusted_dose or "ALT" in adj.adjusted_dose


def test_normal_function_no_adjustment():
    """Normal liver and kidney function should not require dose adjustments."""
    lf = LiverFunction(alt=20, ast=18, tbil=0.5, albumin=4.2)
    rf = RenalFunction(egfr=95, creatinine=0.9)

    assessment = OrganAssessment(lf, rf)
    assert assessment.liver_class == "A"
    assert assessment.ckd_stage == "stage_1"

    issues = assessment.assess_medications(["Metformin", "Sitagliptin"])
    # Normal function should yield minimal issues
    blocked_or_major = [i for i in issues if i.severity in ("blocked", "major")]
    assert len(blocked_or_major) == 0
