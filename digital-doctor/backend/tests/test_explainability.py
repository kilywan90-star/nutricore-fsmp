"""Tests for explainability engine — rule-based feature attribution."""
import pytest

from src.models.explanation import (
    FactorContribution,
    DiagnosisExplanation,
    PrescriptionExplanation,
    RiskExplanation,
)
from src.services.explainability import (
    ExplainabilityEngine,
    generate_explanation_summary,
)


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    return ExplainabilityEngine()


@pytest.fixture
def sample_diagnosis_result():
    return {
        "primary_diagnosis": {
            "type": "2型糖尿病",
            "subtype": None,
            "confidence": "high",
            "guideline_ref": "中国2型糖尿病防治指南(2024版) §4.1",
        },
        "differentials": [
            {
                "condition": "1型糖尿病",
                "probability": "低",
                "supporting_evidence": "成年发病，无酮症倾向",
                "ruling_out_needed": "是",
            },
        ],
        "recommended_tests": [],
        "narrative": "根据指南，诊断为2型糖尿病。",
        "overall_confidence": 0.78,
        "method": "rule_only",
    }


@pytest.fixture
def sample_patient_data():
    return {
        "fpg": 8.2,
        "hba1c": 7.5,
        "bmi": 28.0,
        "age": 55,
        "egfr": 80,
        "gender": "M",
        "diabetes_type": "type2",
        "family_history": True,
        "has_hypertension": True,
    }


@pytest.fixture
def sample_rule_matches():
    return [
        {
            "id": "class-001",
            "name": "2型糖尿病诊断标准",
            "category": "diagnosis",
            "confidence": "high",
            "conclusion": "FPG >= 7.0 mmol/L，符合糖尿病诊断",
            "reference": "中国2型糖尿病防治指南(2024版) §4.1",
            "conditions": [{"field": "fpg", "operator": "gte", "value": 7.0}],
        },
    ]


@pytest.fixture
def sample_prescription_result():
    return {
        "overall_rating": "caution",
        "issues": [
            {
                "severity": "moderate",
                "category": "guideline_concordance",
                "description": "HbA1c=7.5%, 未达标(目标<7.0%)，目前仅1种降糖药",
                "recommendation": "如HbA1c持续不达标>3个月，建议联合第二种药物",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §6.5",
            },
        ],
        "summary": "处方存在用药风险(需关注)",
        "diagnosis": "type2_diabetes",
        "medication_count": 1,
        "issue_count": 1,
    }


@pytest.fixture
def sample_risk_result():
    return {
        "risk_level": "中危",
        "score": 15,
        "max_score": 45,
        "factor_scores": {
            "age_score": 6,
            "bmi_score": 6,
            "waist_score": 0,
            "family_score": 6,
            "activity_score": 0,
            "glucose_score": 5,
            "hypertension_score": 3,
        },
        "recommendations": ["建议3个月后复查空腹血糖"],
    }


# ── Test 1: Diagnosis explanation returns primary factors with guideline refs ─

def test_explain_diagnosis_returns_primary_factors_with_guideline_refs(
    engine, sample_diagnosis_result, sample_patient_data, sample_rule_matches
):
    """explain_diagnosis should return FactorContribution items with guideline_ref fields."""
    explanation = engine.explain_diagnosis(
        sample_diagnosis_result,
        sample_patient_data,
        sample_rule_matches,
    )

    assert isinstance(explanation, DiagnosisExplanation)
    assert explanation.primary_diagnosis == "2型糖尿病"
    assert len(explanation.primary_factors) > 0

    # Each primary factor should have required fields
    for factor in explanation.primary_factors:
        assert isinstance(factor, FactorContribution)
        assert factor.factor != ""
        assert factor.impact in ("positive", "negative", "neutral")
        assert factor.weight > 0.0
        assert factor.guideline_ref != "" or factor.threshold != ""

    # At least one factor should have a guideline reference
    guideline_factors = [f for f in explanation.primary_factors if "中国2型糖尿病防治指南" in f.guideline_ref]
    assert len(guideline_factors) >= 1

    # Summary should be present and non-empty
    assert explanation.summary != ""
    assert "2型糖尿病" in explanation.summary

    # Differentials should be annotated
    assert len(explanation.differentials) >= 0

    # Rule contributions should be present
    assert len(explanation.rule_contributions) >= 1
    rule_ids = [rc["rule_id"] for rc in explanation.rule_contributions]
    assert "class-001" in rule_ids


# ── Test 2: Prescription explanation maps interactions to patient factors ──

def test_explain_prescription_maps_interactions_to_patient_factors(
    engine, sample_prescription_result
):
    """explain_prescription_review should map each issue to contributing patient factors."""
    patient_data = {
        "conditions": ["egfr<30", "heart_failure"],
        "hba1c": 7.5,
        "egfr": 28,
    }

    explanation = engine.explain_prescription_review(
        sample_prescription_result,
        patient_data,
    )

    assert isinstance(explanation, PrescriptionExplanation)
    assert explanation.overall_rating == "caution"
    assert len(explanation.issues) >= 1

    # Each issue should have contributing_factors
    for issue in explanation.issues:
        assert "contributing_factors" in issue
        assert isinstance(issue["contributing_factors"], list)
        assert "recommendation_rationale" in issue
        assert issue["recommendation_rationale"] != ""

    # Summary should reflect the overall rating
    assert "需关注" in explanation.summary or "caution" in explanation.summary.lower()


# ── Test 3: Risk explanation maps modifiable factors correctly ────────────

def test_explain_risk_maps_modifiable_factors_correctly(engine, sample_risk_result):
    """explain_risk_assessment should correctly identify modifiable vs non-modifiable factors."""
    explanation = engine.explain_risk_assessment(
        sample_risk_result,
        sample_risk_result["factor_scores"],
    )

    assert isinstance(explanation, RiskExplanation)
    assert explanation.risk_level == "中危"

    # Modifiable factors: bmi, waist, activity, glucose, hypertension
    modifiable_keys = {f["factor_key"] for f in explanation.modifiable_factors}
    assert "bmi_score" in modifiable_keys, "BMI should be modifiable"
    assert "glucose_score" in modifiable_keys, "Glucose should be modifiable"

    # Age and family history should NOT be in modifiable
    modifiable_keys_set = {f["factor_key"] for f in explanation.modifiable_factors}
    assert "age_score" not in modifiable_keys_set, "Age should not be modifiable"
    assert "family_score" not in modifiable_keys_set, "Family history should not be modifiable"

    # Each modifiable factor should have actionable_advice
    for factor in explanation.modifiable_factors:
        assert "actionable_advice" in factor
        assert factor["actionable_advice"] != ""

    # Contributing factors should be sorted by score descending
    scores = [f["score"] for f in explanation.contributing_factors]
    assert scores == sorted(scores, reverse=True), "Contributing factors should be sorted by score descending"

    # Summary should mention risk level
    assert "中危" in explanation.summary


# ── Test 4: Explanation summary generator produces coherent Chinese text ──

def test_generate_explanation_summary_produces_coherent_chinese():
    """generate_explanation_summary should produce a readable Chinese explanation."""
    factors = [
        FactorContribution(
            factor="空腹血糖(FPG)",
            value="8.2 mmol/L",
            threshold="≥7.0 mmol/L (糖尿病)",
            impact="positive",
            weight=0.25,
            guideline_ref="中国2型糖尿病防治指南(2024版) §4.1",
        ),
        FactorContribution(
            factor="糖化血红蛋白(HbA1c)",
            value="7.5%",
            threshold="≥6.5% (糖尿病)",
            impact="positive",
            weight=0.25,
            guideline_ref="中国2型糖尿病防治指南(2024版) §4.1",
        ),
        FactorContribution(
            factor="BMI（体重指数）",
            value="28.0 kg/m²",
            threshold="≥24 超重，≥28 肥胖",
            impact="positive",
            weight=0.10,
            guideline_ref="中国2型糖尿病防治指南(2024版) §3.2",
        ),
        FactorContribution(
            factor="eGFR",
            value="80 mL/min/1.73m²",
            threshold="≥90 正常, 60–89 轻度降低",
            impact="neutral",
            weight=0.10,
            guideline_ref="中国2型糖尿病防治指南(2024版) §8.3",
        ),
    ]

    summary = generate_explanation_summary(factors, "2型糖尿病")

    assert isinstance(summary, str)
    assert len(summary) > 10
    assert "2型糖尿病" in summary
    assert "8.2" in summary
    assert "7.5" in summary
    assert "28.0" in summary
    # Should contain Chinese guideline reference
    assert "中国2型糖尿病防治指南" in summary
    # Should contain numbered items (①②③)
    assert "①" in summary or "②" in summary


# ── Edge cases ───────────────────────────────────────────────────────────

def test_explain_risk_no_modifiable_factors(engine):
    """All zero scores should produce empty modifiable list."""
    risk_result = {
        "risk_level": "低危",
        "score": 0,
        "max_score": 45,
        "factor_scores": {
            "bmi_score": 0,
            "glucose_score": 0,
            "age_score": 0,
        },
        "recommendations": [],
    }
    explanation = engine.explain_risk_assessment(risk_result, risk_result["factor_scores"])
    assert explanation.risk_level == "低危"
    assert len(explanation.contributing_factors) == 0
    assert len(explanation.modifiable_factors) == 0


def test_explain_diagnosis_minimal_data(engine):
    """Minimal data should not crash and should return valid explanation."""
    diagnosis_result = {
        "primary_diagnosis": {"type": "未明确诊断", "confidence": "low", "guideline_ref": ""},
        "differentials": [],
        "recommended_tests": [],
        "overall_confidence": 0.0,
        "method": "rule_only",
    }
    patient_data = {"age": 30}
    rule_matches = []

    explanation = engine.explain_diagnosis(diagnosis_result, patient_data, rule_matches)

    assert explanation.primary_diagnosis == "未明确诊断"
    assert explanation.confidence == 0.0
    # Should still produce a summary
    assert explanation.summary != ""
