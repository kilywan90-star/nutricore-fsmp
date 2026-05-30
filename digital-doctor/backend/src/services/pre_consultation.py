"""Pre-consultation triage service.

Generates personalized questionnaires, analyzes patient answers,
and produces structured medical summaries for doctor review.
"""

from __future__ import annotations

from src.services.questionnaire_templates import TEMPLATES, get_template


# ── Keyword → template mapping ───────────────────────────────────────────────

_POOR_CONTROL_KEYWORDS = [
    "血糖高", "控制不好", "控制不佳", "血糖波动", "降不下来",
    "忽高忽低", "居高不下", "没控制住", "偏高",
]

_COMPLICATION_KEYWORDS = [
    "眼睛", "视力", "模糊", "看不清",
    "脚", "麻木", "刺痛", "水肿",
    "肾", "泡沫尿", "尿蛋白",
    "胸闷", "心慌", "心悸",
    "并发症",
]


def _select_template(patient_data: dict) -> str:
    """Pick the best template for this patient's profile and complaint."""
    diabetes_type = patient_data.get("diabetes_type", "")
    treatment_stage = patient_data.get("treatment_stage", "")
    chief_complaint = patient_data.get("chief_complaint", "")
    last_visit_findings = patient_data.get("last_visit_findings", "")

    if diabetes_type in ("新诊断", "初诊", "type2_new"):
        return "new_diabetes"

    combined = f"{chief_complaint} {treatment_stage} {last_visit_findings}".lower()

    if any(kw in combined for kw in _COMPLICATION_KEYWORDS):
        return "complication_screening"

    if any(kw in combined for kw in _POOR_CONTROL_KEYWORDS):
        return "follow_up_poor_control"

    if treatment_stage in ("年度复查", "年度评估", "annual_review"):
        return "annual_review"

    hba1c = patient_data.get("hba1c")
    if hba1c is not None and float(hba1c) >= 8.0:
        return "follow_up_poor_control"

    return "follow_up_routine"


# ── Public API ────────────────────────────────────────────────────────────────

def generate_questionnaire(patient_data: dict) -> list[dict]:
    """Generate a personalized questionnaire based on patient profile.

    Args:
        patient_data: dict with keys:
            - chief_complaint (str): patient's stated complaint
            - diabetes_type (str): e.g. 2型糖尿病, 新诊断
            - treatment_stage (str): e.g. 常规复诊, 年度复查
            - last_visit_findings (str): findings from last visit
            - hba1c (float|None): latest HbA1c
            (additional fields are accepted but not required)

    Returns:
        Ordered list of question dicts with {question_id, question_text,
        answer_type, options[], required, depends_on}.
    """
    template_id = _select_template(patient_data)
    template = get_template(template_id)
    if template is None:
        template = get_template("follow_up_routine")

    questions = template["questions"]

    # Merge template context into the first question's text if it has
    # a description about the template category
    processed = []
    for q in questions:
        processed.append({
            "question_id": q["question_id"],
            "question_text": q["question_text"],
            "answer_type": q["answer_type"],
            "options": q["options"],
            "required": q["required"],
            "depends_on": q["depends_on"],
        })

    return processed


def analyze_answers(answers: list[dict], patient_data: dict) -> dict:
    """Analyze submitted questionnaire answers into structured medical data.

    Args:
        answers: list of {question_id, answer_value}
        patient_data: the same patient_data dict passed to generate_questionnaire

    Returns:
        Structured dict with sections:
          - chief_complaint
          - present_illness (HPI)
          - past_history
          - family_history
          - social_history (lifestyle/food/exercise)
          - medication_review
          - review_of_systems
    """
    answers_map = {a["question_id"]: a.get("answer_value", a.get("answer", "")) for a in answers}

    def get_answer(qid: str, default: str = "") -> str:
        return str(answers_map.get(qid, default))

    # ── Chief complaint ──
    chief_complaint = get_answer("chief_complaint") or patient_data.get("chief_complaint", "")

    # ── Present illness (HPI) ──
    hpi_parts = []

    symptom_duration = get_answer("symptom_duration")
    if symptom_duration:
        hpi_parts.append(f"症状持续时间：{symptom_duration}")

    discovery = get_answer("discovery_method")
    if discovery:
        hpi_parts.append(f"发现方式：{discovery}")

    weight_change = get_answer("recent_weight_change")
    if weight_change:
        hpi_parts.append(f"体重变化：{weight_change}")

    glucose_range = get_answer("fasting_glucose_range")
    if glucose_range:
        hpi_parts.append(f"空腹血糖范围：{glucose_range}mmol/L")

    ppg_range = get_answer("postprandial_glucose_range")
    if ppg_range:
        hpi_parts.append(f"餐后血糖范围：{ppg_range}mmol/L")

    fluctuation = get_answer("glucose_fluctuation")
    if fluctuation:
        hpi_parts.append(f"血糖波动特点：{fluctuation}")

    highest = get_answer("highest_glucose")
    if highest:
        hpi_parts.append(f"近期最高血糖：{highest}mmol/L")

    lowest = get_answer("lowest_glucose")
    if lowest:
        hpi_parts.append(f"近期最低血糖：{lowest}mmol/L")

    hypo = get_answer("hypoglycemia_episodes")
    if hypo:
        hypo_detail = get_answer("hypoglycemia_detail")
        hpi_parts.append(f"低血糖事件：{hypo}" + (f"（{hypo_detail}）" if hypo_detail else ""))

    control_reason = get_answer("chief_complaint")
    if control_reason and chief_complaint:
        pass  # chief_complaint already captured

    hba1c_aware = get_answer("hba1c_awareness")
    if hba1c_aware:
        hpi_parts.append(f"HbA1c知晓：{hba1c_aware}")

    glucose_monitor = get_answer("glucose_self_monitoring")
    if glucose_monitor:
        hpi_parts.append(f"自我监测频率：{glucose_monitor}")

    medical_adjust = get_answer("medication_adjustment")
    if medical_adjust:
        hpi_parts.append(f"药物调整：{medical_adjust}")

    hospitalization = get_answer("hospitalization")
    if hospitalization:
        hpi_parts.append(f"住院/急诊：{hospitalization}")

    present_illness = "；".join(hpi_parts) if hpi_parts else "无特殊主诉"

    # ── Past history ──
    past_parts = []
    other_conditions = get_answer("other_conditions")
    if other_conditions:
        past_parts.append(f"合并疾病：{other_conditions}")

    prev_diagnosis = get_answer("previous_diagnosis")
    if prev_diagnosis:
        past_parts.append(f"既往诊断：{prev_diagnosis}")

    current_meds = get_answer("current_medications")
    if current_meds:
        past_parts.append(f"其他用药：{current_meds}")

    past_history = "；".join(past_parts) if past_parts else "无特殊既往史"

    # ── Family history ──
    family_diabetes = get_answer("family_diabetes")
    family_history = f"糖尿病家族史：{family_diabetes}" if family_diabetes else "糖尿病家族史：不详"

    # ── Social history (lifestyle/food/exercise) ──
    social_parts = []

    diet_habit = get_answer("diet_habit")
    if diet_habit:
        social_parts.append(f"饮食偏好：{diet_habit}")

    diet_adherence = get_answer("diet_adherence")
    if diet_adherence:
        social_parts.append(f"饮食依从性：{diet_adherence}")

    meal_pattern = get_answer("meal_pattern")
    if meal_pattern:
        social_parts.append(f"进餐规律：{meal_pattern}")

    staple = get_answer("staple_food_amount")
    if staple:
        social_parts.append(f"主食量：{staple}")

    sugary = get_answer("sugary_drinks")
    if sugary:
        social_parts.append(f"含糖饮料：{sugary}")

    alcohol = get_answer("alcohol_use")
    if alcohol:
        social_parts.append(f"饮酒：{alcohol}")

    exercise = get_answer("exercise_frequency") or get_answer("exercise_adherence")
    if exercise:
        social_parts.append(f"运动：{exercise}")

    sleep = get_answer("sleep_quality")
    if sleep:
        social_parts.append(f"睡眠：{sleep}")

    stress = get_answer("stress_level")
    if stress:
        social_parts.append(f"精神压力：{stress}")

    lifestyle_change = get_answer("lifestyle_change")
    if lifestyle_change:
        social_parts.append(f"生活方式改变：{lifestyle_change}")

    management_goals = get_answer("management_goals")
    if management_goals:
        social_parts.append(f"管理目标：{management_goals}")

    mental = get_answer("mental_health")
    if mental:
        social_parts.append(f"心理影响：{mental}")

    social_history = "；".join(social_parts) if social_parts else "无特殊生活方式信息"

    # ── Medication review ──
    med_parts = []
    med_adherence = get_answer("medication_adherence")
    if med_adherence:
        med_parts.append(f"服药依从性：{med_adherence}")
    side_effects = get_answer("medication_side_effects")
    if side_effects:
        med_parts.append(f"药物不良反应：{side_effects}")
    med_barrier = get_answer("medication_barrier")
    if med_barrier:
        med_parts.append(f"用药困难：{med_barrier}")
    immunization = get_answer("immunization")
    if immunization:
        med_parts.append(f"流感疫苗：{immunization}")
    medication_review = "；".join(med_parts) if med_parts else "无特殊用药问题"

    # ── Review of systems ──
    ros_parts = []
    vision = get_answer("vision_changes")
    if vision:
        ros_parts.append(f"视力：{vision}")
    eye_exam = get_answer("last_eye_exam")
    if eye_exam:
        ros_parts.append(f"眼底检查：{eye_exam}")
    edema = get_answer("edema")
    if edema:
        ros_parts.append(f"水肿：{edema}")
    urine = get_answer("urine_foam")
    if urine:
        ros_parts.append(f"泡沫尿：{urine}")
    numbness = get_answer("numbness")
    if numbness:
        ros_parts.append(f"神经症状：{numbness}")
    foot_check = get_answer("foot_check")
    if foot_check:
        ros_parts.append(f"足部检查习惯：{foot_check}")
    foot_issues = get_answer("foot_issues")
    if foot_issues:
        ros_parts.append(f"足部问题：{foot_issues}")
    chest = get_answer("chest_pain")
    if chest:
        ros_parts.append(f"心血管症状：{chest}")
    bp = get_answer("blood_pressure_control")
    if bp:
        ros_parts.append(f"血压：{bp}")
    lipid = get_answer("lipid_control")
    if lipid:
        ros_parts.append(f"血脂：{lipid}")

    annual_eye = get_answer("annual_eye_exam")
    if annual_eye:
        ros_parts.append(f"年度眼科检查：{annual_eye}")
    annual_kidney = get_answer("annual_kidney_check")
    if annual_kidney:
        ros_parts.append(f"年度肾功能检查：{annual_kidney}")
    annual_foot = get_answer("annual_foot_exam")
    if annual_foot:
        ros_parts.append(f"年度足部检查：{annual_foot}")
    annual_lipid = get_answer("annual_lipid_check")
    if annual_lipid:
        ros_parts.append(f"年度血脂检查：{annual_lipid}")

    review_of_systems = "；".join(ros_parts) if ros_parts else "无特殊系统回顾异常"

    return {
        "chief_complaint": chief_complaint,
        "present_illness": present_illness,
        "past_history": past_history,
        "family_history": family_history,
        "social_history": social_history,
        "medication_review": medication_review,
        "review_of_systems": review_of_systems,
    }


def generate_doctor_summary(pre_consult_data: dict) -> str:
    """Format structured pre-consultation data into a concise Chinese medical
    summary paragraph (200-300 characters, suitable for quick doctor review).

    Args:
        pre_consult_data: the dict returned by analyze_answers()

    Returns:
        A single-string paragraph summary in Chinese.
    """
    cc = pre_consult_data.get("chief_complaint", "")
    hpi = pre_consult_data.get("present_illness", "")
    past = pre_consult_data.get("past_history", "")
    family = pre_consult_data.get("family_history", "")
    social = pre_consult_data.get("social_history", "")
    med = pre_consult_data.get("medication_review", "")
    ros = pre_consult_data.get("review_of_systems", "")

    lines = []

    # Opening: chief complaint
    if cc and cc != "无特殊主诉":
        lines.append(f"患者主诉：{cc}。")
    else:
        lines.append("患者本次复诊，无明显特殊主诉。")

    # HPI
    if hpi and hpi != "无特殊主诉":
        lines.append(f"现病史：{hpi}。")

    # Past history (only if notable)
    if past and past != "无特殊既往史":
        lines.append(f"既往史：{past}。")

    # Family history (only if positive)
    if family and "有" in family and "没有" not in family and "不详" not in family:
        lines.append(f"家族史：{family}。")

    # Social / lifestyle
    if social and social != "无特殊生活方式信息":
        lines.append(f"生活情况及社会史：{social}。")

    # Medication
    if med and med != "无特殊用药问题":
        lines.append(f"用药情况：{med}。")

    # Review of systems (only if notable)
    if ros and ros != "无特殊系统回顾异常":
        lines.append(f"系统回顾：{ros}。")

    full = "".join(lines)

    # Truncate to ~300 characters, breaking at sentence boundary if possible
    if len(full) > 310:
        cutoff = full.rfind("。", 250, 310)
        if cutoff > 0:
            full = full[:cutoff + 1]

    return full
