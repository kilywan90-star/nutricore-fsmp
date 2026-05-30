from fastapi import APIRouter, HTTPException

from ..models.assessment import NutritionScreeningInput, NRS2002Result
from ..engine import score_nrs2002, calculate_bmi

router = APIRouter()


@router.post("/nrs2002", response_model=NRS2002Result)
async def screen_nutrition_risk(screening: NutritionScreeningInput):
    """
    NRS 2002 Nutrition Risk Screening.

    Input patient demographics, disease, and nutritional parameters.
    Returns NRS 2002 score with risk level and intervention trigger.
    """
    if screening.patient.bmi == 0:
        screening.patient.bmi = calculate_bmi(
            screening.patient.weight_kg,
            screening.patient.height_cm,
        )

    result = score_nrs2002(screening)
    return result


@router.get("/nrs2002/reference")
async def nrs2002_reference():
    """NRS 2002 scoring reference table."""
    return {
        "impaired_nutritional_status": {
            "0": "Normal nutritional status",
            "1": "Weight loss >5% in 3 months OR food intake 50-75% of normal in preceding week",
            "2": "Weight loss >5% in 2 months OR BMI 18.5-20.5 + impaired general condition OR food intake 25-50%",
            "3": "Weight loss >5% in 1 month OR BMI <18.5 + impaired general condition OR food intake 0-25%",
        },
        "disease_severity": {
            "0": "Normal nutritional requirements",
            "1": "Hip fracture, chronic disease with acute complications (COPD, cirrhosis, chronic dialysis, diabetes, oncology)",
            "2": "Major abdominal surgery, stroke, severe pneumonia, hematologic malignancy",
            "3": "Head injury, bone marrow transplant, ICU patients (APACHE >10)",
        },
        "age_adjustment": "Add 1 point if age >= 70 years",
        "interpretation": {
            "score_0_2": "Low risk — re-screen weekly",
            "score_3_4": "Medium risk — nutrition intervention indicated",
            "score_5_7": "High risk — urgent nutrition intervention",
        },
    }
