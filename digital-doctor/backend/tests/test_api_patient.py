import pytest
from src.api.patient import assess_diabetes_risk, health_coach_chat
from src.api.patient import RiskAssessmentRequest, HealthCoachRequest


@pytest.mark.asyncio
async def test_risk_assessment_endpoint():
    """Test the risk assessment endpoint function directly"""
    req = RiskAssessmentRequest(
        age=55,
        bmi=28.5,
        waist_circumference=95,
        family_history=True,
        physical_activity="low",
        fasting_glucose=6.8,
        has_hypertension=True,
    )
    result = await assess_diabetes_risk(req)
    assert result["risk_level"] in ("高危", "极高危")
    assert result["score"] >= 15
    assert "factor_scores" in result
    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_health_coach_endpoint():
    """Test the health coach endpoint function directly"""
    req = HealthCoachRequest(
        message="我最近血糖有点高，怎么办？",
        recent_fpg=[7.5, 7.8, 7.2],
        recent_ppg=[10.0, 9.5],
        hba1c=7.5,
        medications=["二甲双胍 500mg bid"],
        diet_adherence="一般",
        exercise_adherence="较差",
    )
    response = await health_coach_chat(req)
    assert response.reply is not None
    assert len(response.reply) > 0
    assert isinstance(response.is_urgent, bool)
    # "血糖有点高" is not an urgent keyword
    assert response.is_urgent is False
