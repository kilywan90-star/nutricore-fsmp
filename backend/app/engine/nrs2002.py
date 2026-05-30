from ..models.assessment import NRS2002Result, NutritionScreeningInput, PatientInfo


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """BMI = weight(kg) / height(m)^2"""
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def score_nrs2002(screening: NutritionScreeningInput) -> NRS2002Result:
    """
    NRS 2002 营养风险筛查评分

    Components:
    A. Impaired nutritional status (0-3): based on BMI, weight loss, food intake
    B. Severity of disease (0-3): metabolic stress level
    C. Age adjustment: +1 if >= 70 years
    """
    breakdown = {}
    p = screening.patient

    # Part A: Nutritional status impairment
    nutrient_score = 0
    if p.bmi < 18.5:
        nutrient_score = 3
    elif p.bmi < 20.5:
        nutrient_score = 2
    elif screening.weight_loss_3m_kg > 0 and p.weight_kg > 0:
        loss_pct = screening.weight_loss_3m_kg / p.weight_kg * 100
        if loss_pct > 15:
            nutrient_score = 3
        elif loss_pct > 5:
            nutrient_score = 2
        else:
            nutrient_score = 1
    else:
        nutrient_score = 1

    if screening.food_intake_reduction_pct >= 75:
        nutrient_score = max(nutrient_score, 3)
    elif screening.food_intake_reduction_pct >= 50:
        nutrient_score = max(nutrient_score, 2)
    elif screening.food_intake_reduction_pct >= 25:
        nutrient_score = max(nutrient_score, 1)

    breakdown["impaired_nutritional_status"] = nutrient_score

    # Part B: Disease severity (metabolic stress)
    disease_score = _score_disease_severity(screening)
    breakdown["disease_severity"] = disease_score

    # Part C: Age adjustment
    age_score = 1 if p.age >= 70 else 0
    breakdown["age_adjustment"] = age_score

    total = nutrient_score + disease_score + age_score

    if total >= 5:
        risk_level = "high"
    elif total >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return NRS2002Result(
        score=total,
        risk_level=risk_level,
        breakdown=breakdown,
        triggers_intervention=total >= 3,
    )


def _score_disease_severity(screening: NutritionScreeningInput) -> int:
    """
    Disease severity scoring for NRS 2002:
    0 = normal nutritional requirements
    1 = chronic disease with complications (hip fracture, COPD, cirrhosis, etc.)
    2 = major abdominal surgery, severe pneumonia, stroke, hematologic malignancy
    3 = severe head injury, bone marrow transplant, ICU (APACHE > 10)
    """
    surgical_severe = {
        "pancreaticoduodenectomy",  # 胰十二指肠切除术
        "esophagectomy",  # 食管癌根治术
        "total_gastrectomy",  # 全胃切除术
        "liver_resection_major",  # 大范围肝切除术
        "cytoreductive_surgery",  # 肿瘤减灭术
    }

    surgical_moderate = {
        "colorectal_resection",  # 结直肠癌根治术
        "gastrectomy_subtotal",  # 胃大部切除术
        "cholecystectomy",  # 胆囊切除术
        "appendectomy",  # 阑尾切除术
        "hernia_repair",  # 疝修补术
    }

    if screening.surgery_code:
        if screening.surgery_code in surgical_severe:
            return 3
        if screening.surgery_code in surgical_moderate:
            return 2
        return 1

    # Non-surgical disease scoring
    severe_disease_codes = (
        "1E71",  # severe sepsis
        "1D53",  # bone marrow transplant
        "NA07",  # traumatic brain injury
    )
    moderate_disease_codes = (
        "2C25",  # major GI cancer
        "CA40",  # severe pneumonia
        "8B20",  # stroke
    )

    if screening.disease_icd11_code in severe_disease_codes:
        return 3
    if screening.disease_icd11_code in moderate_disease_codes:
        return 2
    return 1
