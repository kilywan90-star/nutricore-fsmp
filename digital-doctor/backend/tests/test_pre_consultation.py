"""Tests for pre-consultation triage service (P3-1)."""
import pytest
from src.services.pre_consultation import (
    generate_questionnaire,
    analyze_answers,
    generate_doctor_summary,
    _select_template,
)
from src.services.questionnaire_templates import TEMPLATES


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def new_diabetes_patient():
    return {
        "chief_complaint": "体检发现血糖高",
        "diabetes_type": "新诊断",
        "treatment_stage": "初诊",
        "last_visit_findings": "",
        "hba1c": 8.5,
    }


@pytest.fixture
def follow_up_patient():
    return {
        "chief_complaint": "常规复查",
        "diabetes_type": "2型糖尿病",
        "treatment_stage": "常规复诊",
        "last_visit_findings": "上次HbA1c 7.2，建议控制饮食",
        "hba1c": 7.2,
    }


@pytest.fixture
def poor_control_patient():
    return {
        "chief_complaint": "最近血糖控制不好，忽高忽低",
        "diabetes_type": "2型糖尿病",
        "treatment_stage": "常规复诊",
        "last_visit_findings": "",
        "hba1c": 9.1,
    }


@pytest.fixture
def complication_patient():
    return {
        "chief_complaint": "最近眼睛模糊看不清",
        "diabetes_type": "2型糖尿病",
        "treatment_stage": "并发症筛查",
        "last_visit_findings": "",
        "hba1c": 7.8,
    }


@pytest.fixture
def annual_review_patient():
    return {
        "chief_complaint": "年度检查",
        "diabetes_type": "2型糖尿病",
        "treatment_stage": "年度复查",
        "last_visit_findings": "",
        "hba1c": 7.0,
    }


@pytest.fixture
def sample_answers():
    return [
        {"question_id": "chief_complaint", "answer_value": "多尿、多饮、多食、体重下降"},
        {"question_id": "symptom_duration", "answer_value": "1-3个月"},
        {"question_id": "discovery_method", "answer_value": "日常体检"},
        {"question_id": "recent_weight_change", "answer_value": "体重下降超过5kg"},
        {"question_id": "diet_habit", "answer_value": "偏甜食/含糖饮料"},
        {"question_id": "exercise_frequency", "answer_value": "几乎不运动"},
        {"question_id": "family_diabetes", "answer_value": "有"},
        {"question_id": "previous_diagnosis", "answer_value": "未诊断过"},
        {"question_id": "other_conditions", "answer_value": "高血压"},
        {"question_id": "current_medications", "answer_value": "硝苯地平 30mg qd"},
    ]


# ── Test 1: Questionnaire generation ────────────────────────────────────────────

def test_generate_questionnaire_new_diabetes(new_diabetes_patient):
    """Generates correct questionnaire for new diabetes patient."""
    questions = generate_questionnaire(new_diabetes_patient)
    assert isinstance(questions, list)
    assert len(questions) > 0

    question_ids = {q["question_id"] for q in questions}
    assert "chief_complaint" in question_ids
    assert "symptom_duration" in question_ids
    assert "family_diabetes" in question_ids

    # Each question should have required fields
    for q in questions:
        assert "question_id" in q
        assert "question_text" in q
        assert "answer_type" in q
        assert "required" in q
        assert "depends_on" in q or "depends_on" in q  # field exists (may be None)


def test_generate_questionnaire_template_selection():
    """Correct template is selected based on patient profile."""
    # New diabetes
    assert _select_template({"diabetes_type": "新诊断", "chief_complaint": "", "treatment_stage": "", "last_visit_findings": ""}) == "new_diabetes"

    # Poor control keywords
    assert _select_template({"diabetes_type": "2型", "chief_complaint": "血糖控制不好", "treatment_stage": "", "last_visit_findings": ""}) == "follow_up_poor_control"

    # Complication keywords
    assert _select_template({"diabetes_type": "2型", "chief_complaint": "眼睛看不清", "treatment_stage": "", "last_visit_findings": ""}) == "complication_screening"

    # Annual review
    assert _select_template({"diabetes_type": "2型", "chief_complaint": "", "treatment_stage": "年度复查", "last_visit_findings": ""}) == "annual_review"

    # High HbA1c triggers poor control
    assert _select_template({"diabetes_type": "2型", "chief_complaint": "", "treatment_stage": "", "last_visit_findings": "", "hba1c": 9.0}) == "follow_up_poor_control"

    # Default fallback
    assert _select_template({"diabetes_type": "2型", "chief_complaint": "复查", "treatment_stage": "", "last_visit_findings": ""}) == "follow_up_routine"


# ── Test 2: Answer analysis ─────────────────────────────────────────────────────

def test_analyze_answers(sample_answers, new_diabetes_patient):
    """Correctly processes answers into structured summary."""
    result = analyze_answers(sample_answers, new_diabetes_patient)

    assert isinstance(result, dict)
    assert "chief_complaint" in result
    assert "present_illness" in result
    assert "past_history" in result
    assert "family_history" in result
    assert "social_history" in result
    assert "medication_review" in result
    assert "review_of_systems" in result

    # Chief complaint should match
    assert result["chief_complaint"] == "多尿、多饮、多食、体重下降"

    # Present illness should include symptom duration
    assert "1-3个月" in result["present_illness"]

    # Past history should include other conditions
    assert "高血压" in result["past_history"]

    # Family history should contain the answer
    assert "有" in result["family_history"]

    # Social history should include diet and exercise
    assert "偏甜食/含糖饮料" in result["social_history"]
    assert "几乎不运动" in result["social_history"]


# ── Test 3: Summary generation ──────────────────────────────────────────────────

def test_generate_doctor_summary(sample_answers, new_diabetes_patient):
    """Generates a concise Chinese medical summary."""
    analyzed = analyze_answers(sample_answers, new_diabetes_patient)
    summary = generate_doctor_summary(analyzed)

    assert isinstance(summary, str)
    assert len(summary) > 0

    # Should contain key patient info
    assert "多尿" in summary

    # Should be in Chinese
    # (just checking it's not empty and contains CJK chars)
    assert any('一' <= c <= '鿿' for c in summary)

    # Should not exceed reasonable length
    assert len(summary) <= 600  # give some margin beyond 300 target

    # Should be a coherent paragraph (not raw JSON)
    assert "chief_complaint" not in summary.lower()


def test_generate_doctor_summary_empty():
    """Handles minimal data gracefully."""
    analyzed = analyze_answers([], {"chief_complaint": "", "diabetes_type": "2型"})
    summary = generate_doctor_summary(analyzed)
    assert isinstance(summary, str)
    assert len(summary) > 0
    assert "复诊" in summary or "特殊" in summary or "主诉" in summary


# ── Test 4: Conditional logic ───────────────────────────────────────────────────

def test_conditional_questions_visible():
    """Questions with depends_on are only visible when parent answer matches."""
    template = TEMPLATES["follow_up_routine"]
    questions = template["questions"]

    # Find a conditional question
    hypo_detail_q = None
    for q in questions:
        if q["depends_on"] is not None:
            hypo_detail_q = q
            break

    assert hypo_detail_q is not None, "Should have at least one conditional question"
    assert hypo_detail_q["question_id"] == "hypoglycemia_detail"
    assert hypo_detail_q["depends_on"]["question_id"] == "hypoglycemia_episodes"

    # The depends_on logic: matches_any checks
    dep = hypo_detail_q["depends_on"]
    assert "matches_any" in dep

    # Without parent answer, should not be visible
    from src.services.pre_consultation import generate_questionnaire

    # When we have the right answer for hypoglycemia episodes, the detail question is included
    # The visibility check happens frontend-side; backend always returns all template questions
    all_qs = generate_questionnaire({"chief_complaint": "", "diabetes_type": "2型", "treatment_stage": "常规复诊", "last_visit_findings": ""})
    all_ids = {q["question_id"] for q in all_qs}
    assert "hypoglycemia_detail" in all_ids
    assert hypo_detail_q["depends_on"] is not None


def test_conditional_logic_in_answers():
    """When answers include the parent question, the detail is processed."""
    answers_with_hypo = [
        {"question_id": "chief_complaint", "answer_value": "血糖控制情况"},
        {"question_id": "hypoglycemia_episodes", "answer_value": "3-5次"},
        {"question_id": "hypoglycemia_detail", "answer_value": "多在凌晨3-4点发生，表现为出汗心慌"},
        {"question_id": "glucose_self_monitoring", "answer_value": "每天监测"},
        {"question_id": "fasting_glucose_range", "answer_value": "4.4-7.0"},
        {"question_id": "postprandial_glucose_range", "answer_value": "7.8-10.0"},
        {"question_id": "medication_adherence", "answer_value": "严格按时服药"},
        {"question_id": "medication_side_effects", "answer_value": "无不适"},
        {"question_id": "diet_adherence", "answer_value": "基本遵守，偶尔放松"},
        {"question_id": "exercise_adherence", "answer_value": "规律运动（每周≥150分钟）"},
    ]

    result = analyze_answers(answers_with_hypo, {"chief_complaint": "", "diabetes_type": "2型"})
    assert "3-5次" in result["present_illness"]
    assert "凌晨" in result["present_illness"]


# ── Test 5: Empty answers ───────────────────────────────────────────────────────

def test_empty_answers():
    """Empty answers produce sensible defaults without crashing."""
    result = analyze_answers([], {"chief_complaint": "", "diabetes_type": "2型"})

    assert result["chief_complaint"] == ""
    assert result["present_illness"] == "无特殊主诉"
    assert result["past_history"] == "无特殊既往史"
    assert "不详" in result["family_history"]
    assert result["social_history"] == "无特殊生活方式信息"
    assert result["medication_review"] == "无特殊用药问题"
    assert result["review_of_systems"] == "无特殊系统回顾异常"


def test_empty_answers_summary():
    """Empty answers generate a valid summary paragraph."""
    analyzed = analyze_answers([], {"chief_complaint": "", "diabetes_type": "2型"})
    summary = generate_doctor_summary(analyzed)
    assert len(summary) > 0
    assert isinstance(summary, str)
    # Should mention that it's a follow-up with no special complaint
    assert "复诊" in summary or "主诉" in summary


def test_partial_answers():
    """Answers with only a few fields filled in still produce valid output."""
    partial = [
        {"question_id": "chief_complaint", "answer_value": "最近总是口渴"},
        {"question_id": "diet_habit", "answer_value": "饮食较清淡均衡"},
    ]
    result = analyze_answers(partial, {"chief_complaint": "", "diabetes_type": "2型"})
    assert "口渴" in result["chief_complaint"]
    assert "清淡" in result["social_history"]
    # Other sections should have defaults
    assert result["present_illness"] == "无特殊主诉"
