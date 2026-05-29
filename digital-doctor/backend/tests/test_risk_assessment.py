import pytest
from src.services.risk_assessment import calculate_diabetes_risk, RiskLevel


def test_calculate_risk_high():
    result = calculate_diabetes_risk(
        age=55,
        bmi=28.5,
        waist_circumference=95,
        family_history=True,
        physical_activity="low",
        fasting_glucose=6.8,
        has_hypertension=True,
    )
    assert result["risk_level"] in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]
    assert result["score"] >= 15


def test_calculate_risk_low():
    result = calculate_diabetes_risk(
        age=30,
        bmi=21.0,
        waist_circumference=75,
        family_history=False,
        physical_activity="high",
        fasting_glucose=5.0,
        has_hypertension=False,
    )
    assert result["risk_level"] == RiskLevel.LOW
    assert result["score"] < 7


def test_calculate_risk_moderate():
    result = calculate_diabetes_risk(
        age=40,
        bmi=25.0,
        waist_circumference=82,
        family_history=False,
        physical_activity="moderate",
        fasting_glucose=5.8,
        has_hypertension=False,
    )
    assert result["risk_level"] == RiskLevel.MODERATE


def test_risk_result_has_recommendations():
    result = calculate_diabetes_risk(
        age=50, bmi=27, waist_circumference=90,
        family_history=True, physical_activity="low",
        fasting_glucose=6.5, has_hypertension=True,
    )
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0


def test_risk_result_includes_breakdown():
    result = calculate_diabetes_risk(
        age=40, bmi=24, waist_circumference=80,
        family_history=False, physical_activity="moderate",
        fasting_glucose=5.5, has_hypertension=False,
    )
    assert "factor_scores" in result
    assert "age_score" in result["factor_scores"]
