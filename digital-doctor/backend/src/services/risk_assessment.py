from enum import Enum


class RiskLevel(str, Enum):
    LOW = "低危"
    MODERATE = "中危"
    HIGH = "高危"
    VERY_HIGH = "极高危"


def calculate_diabetes_risk(
    age: int,
    bmi: float,
    waist_circumference: float,
    family_history: bool,
    physical_activity: str,
    fasting_glucose: float,
    has_hypertension: bool,
) -> dict:
    scores = {}

    # 年龄评分
    if age < 35:
        scores["age_score"] = 0
    elif age < 45:
        scores["age_score"] = 2
    elif age < 55:
        scores["age_score"] = 4
    elif age < 65:
        scores["age_score"] = 6
    else:
        scores["age_score"] = 8

    # BMI评分
    if bmi < 24:
        scores["bmi_score"] = 0
    elif bmi < 28:
        scores["bmi_score"] = 3
    else:
        scores["bmi_score"] = 6

    # 腰围评分（男性≥90, 女性≥85）
    if waist_circumference < 85:
        scores["waist_score"] = 0
    elif waist_circumference < 95:
        scores["waist_score"] = 3
    else:
        scores["waist_score"] = 6

    # 家族史
    scores["family_score"] = 6 if family_history else 0

    # 体力活动
    activity_scores = {"high": 0, "moderate": 2, "low": 4}
    scores["activity_score"] = activity_scores.get(physical_activity, 2)

    # 空腹血糖
    if fasting_glucose < 5.6:
        scores["glucose_score"] = 0
    elif fasting_glucose < 6.1:
        scores["glucose_score"] = 5
    elif fasting_glucose < 7.0:
        scores["glucose_score"] = 8
    else:
        scores["glucose_score"] = 12

    # 高血压
    scores["hypertension_score"] = 3 if has_hypertension else 0

    total = sum(scores.values())

    if total <= 6:
        risk_level = RiskLevel.LOW
    elif total <= 12:
        risk_level = RiskLevel.MODERATE
    elif total <= 20:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.VERY_HIGH

    recommendations = _get_recommendations(risk_level, fasting_glucose, bmi)

    return {
        "risk_level": risk_level,
        "score": total,
        "max_score": 45,
        "factor_scores": scores,
        "recommendations": recommendations,
    }


def _get_recommendations(risk_level: RiskLevel, fpg: float, bmi: float) -> list[str]:
    recs = []
    if risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH):
        recs.append("建议近期到内分泌科就诊，行OGTT+糖化血红蛋白检查")
    elif risk_level == RiskLevel.MODERATE:
        recs.append("建议3个月后复查空腹血糖，并行OGTT筛查")

    if fpg >= 6.1:
        recs.append("空腹血糖偏高，请注意控制饮食碳水化合物摄入")
    if bmi >= 24:
        recs.append("体重超标，建议减重5-10%，每周至少150分钟中等强度运动")
    if risk_level == RiskLevel.LOW:
        recs.append("风险较低，保持健康生活方式，每年体检关注血糖")
    recs.append("建议每日主食控制在250-400g，减少含糖饮料摄入")

    return recs
