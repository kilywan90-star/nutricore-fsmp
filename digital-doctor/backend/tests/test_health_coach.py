# digital-doctor/backend/tests/test_health_coach.py
import pytest
from datetime import datetime
from src.services.health_coach import HealthCoach, CoachContext


@pytest.fixture
def coach():
    return HealthCoach()


@pytest.fixture
def context():
    return CoachContext(
        patient_id="test-001",
        recent_fpg=[6.5, 6.8, 7.0],
        recent_ppg=[9.0, 8.5, 9.5],
        hba1c=7.2,
        medications=["二甲双胍 500mg bid"],
        diet_adherence="一般",
        exercise_adherence="较差",
    )


def test_coach_build_system_prompt(coach, context):
    prompt = coach._build_system_prompt(context)
    assert "2型糖尿病" in prompt
    assert "指南" in prompt
    assert "7.2" in prompt


def test_coach_generate_reply_mock(coach, context):
    reply = coach._mock_reply(context, "我最近血糖有点高")
    assert len(reply) > 0


def test_coach_context_from_patient():
    ctx = CoachContext.from_patient_data(
        patient_id="p1",
        glucose_records=[
            {"value_mmol_l": 6.5, "measure_type": "fasting"},
            {"value_mmol_l": 6.8, "measure_type": "fasting"},
        ],
        hba1c=7.0,
        medications=["二甲双胍"],
    )
    assert ctx.recent_fpg == [6.5, 6.8]


def test_coach_detect_urgent_keywords(coach):
    assert coach._has_urgent_keywords("我感觉心慌出冷汗")
    assert coach._has_urgent_keywords("血糖很高测不出来")
    assert not coach._has_urgent_keywords("今天血糖正常谢谢")
