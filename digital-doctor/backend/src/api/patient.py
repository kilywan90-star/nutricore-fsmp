from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

from src.api.deps import (
    get_health_coach, get_rule_engine,
    calculate_diabetes_risk, interpret_lab_report,
    calculate_glucose_stats, TimeInRange,
    generate_daily_schedule, check_missed_doses,
    check_glucose_alerts,
    CoachContext,
)

router = APIRouter()


class RiskAssessmentRequest(BaseModel):
    age: int = Field(ge=18, le=120)
    bmi: float = Field(ge=10, le=60)
    waist_circumference: float = Field(ge=50, le=200)
    family_history: bool
    physical_activity: str = Field(pattern="^(high|moderate|low)$")
    fasting_glucose: float = Field(ge=2.0, le=30.0)
    has_hypertension: bool


class RiskAssessmentResponse(BaseModel):
    risk_level: str
    score: int
    max_score: int
    factor_scores: dict
    recommendations: list[str]


@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
async def assess_diabetes_risk(req: RiskAssessmentRequest):
    result = calculate_diabetes_risk(
        age=req.age,
        bmi=req.bmi,
        waist_circumference=req.waist_circumference,
        family_history=req.family_history,
        physical_activity=req.physical_activity,
        fasting_glucose=req.fasting_glucose,
        has_hypertension=req.has_hypertension,
    )
    return result


class ReportInterpretRequest(BaseModel):
    report_type: str
    results: dict


@router.post("/report-interpret")
async def interpret_report(req: ReportInterpretRequest):
    return interpret_lab_report(req.report_type, req.results)


class GlucoseLogRequest(BaseModel):
    value_mmol_l: float = Field(ge=1.0, le=40.0)
    measure_type: str = Field(pattern="^(fasting|pre_meal|post_prandial|bedtime|random)$")
    recorded_at: datetime
    notes: Optional[str] = None


class GlucoseStatsResponse(BaseModel):
    count: int
    avg: Optional[float]
    max: Optional[float]
    min: Optional[float]
    time_in_range: Optional[dict]


@router.post("/glucose-stats", response_model=GlucoseStatsResponse)
async def glucose_statistics(values: list[float]):
    stats = calculate_glucose_stats(values)
    tir = TimeInRange(values) if values else None
    return {
        **stats,
        "time_in_range": {
            "in_range_pct": tir.in_range_pct,
            "above_range_pct": tir.above_range_pct,
            "below_range_pct": tir.below_range_pct,
        } if tir else None,
    }


class HealthCoachRequest(BaseModel):
    message: str
    recent_fpg: list[float] = []
    recent_ppg: list[float] = []
    hba1c: Optional[float] = None
    medications: list[str] = []
    diet_adherence: str = "未知"
    exercise_adherence: str = "未知"


class HealthCoachResponse(BaseModel):
    reply: str
    is_urgent: bool


@router.post("/health-coach", response_model=HealthCoachResponse)
async def health_coach_chat(req: HealthCoachRequest):
    coach = get_health_coach()
    ctx = CoachContext(
        patient_id="anonymous",
        recent_fpg=req.recent_fpg,
        recent_ppg=req.recent_ppg,
        hba1c=req.hba1c,
        medications=req.medications,
        diet_adherence=req.diet_adherence,
        exercise_adherence=req.exercise_adherence,
    )
    is_urgent = coach._has_urgent_keywords(req.message)
    reply = await coach.get_reply(ctx, req.message)
    return HealthCoachResponse(reply=reply, is_urgent=is_urgent)
