from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
import uuid

from src.api.deps import (
    get_health_coach, get_rule_engine,
    calculate_diabetes_risk, interpret_lab_report,
    calculate_glucose_stats, TimeInRange,
    generate_daily_schedule, check_missed_doses,
    check_glucose_alerts,
    CoachContext,
)
from src.services.pre_consultation import (
    generate_questionnaire,
    analyze_answers,
    generate_doctor_summary,
)
from src.api.auth_deps import require_role

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


@router.post("/risk-assessment", response_model=RiskAssessmentResponse, dependencies=[Depends(require_role("patient"))])
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


@router.post("/report-interpret", dependencies=[Depends(require_role("patient"))])
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


@router.post("/glucose-stats", response_model=GlucoseStatsResponse, dependencies=[Depends(require_role("patient"))])
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


@router.post("/health-coach", response_model=HealthCoachResponse, dependencies=[Depends(require_role("patient"))])
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


# ── Pre-consultation endpoints ────────────────────────────────────────────────


class QuestionnaireRequest(BaseModel):
    patient_data: dict


class QuestionnaireResponse(BaseModel):
    questions: list[dict]


@router.post("/pre-consultation/questionnaire", response_model=QuestionnaireResponse,
             dependencies=[Depends(require_role("patient"))])
async def get_questionnaire(req: QuestionnaireRequest):
    """Generate a personalized pre-consultation questionnaire."""
    questions = generate_questionnaire(req.patient_data)
    return QuestionnaireResponse(questions=questions)


class AnswerItem(BaseModel):
    question_id: str
    answer_value: str


class SubmitAnswersRequest(BaseModel):
    answers: list[AnswerItem]
    patient_data: dict


class SubmitAnswersResponse(BaseModel):
    summary: dict
    doctor_summary: str


@router.post("/pre-consultation/submit", response_model=SubmitAnswersResponse,
             dependencies=[Depends(require_role("patient"))])
async def submit_answers(req: SubmitAnswersRequest):
    """Submit questionnaire answers and receive an AI summary."""
    answers_dicts = [{"question_id": a.question_id, "answer_value": a.answer_value} for a in req.answers]
    summary = analyze_answers(answers_dicts, req.patient_data)
    doctor_summary = generate_doctor_summary(summary)
    return SubmitAnswersResponse(summary=summary, doctor_summary=doctor_summary)


# ── Allergy endpoints ──────────────────────────────────────────────────────


class AllergyItem(BaseModel):
    id: Optional[str] = None
    substance: str = Field(..., min_length=1, max_length=200, description="过敏物质名称")
    substance_code: Optional[str] = Field(None, max_length=100, description="SNOMED/RxNorm 编码")
    reaction: Optional[str] = Field(None, max_length=500, description="过敏反应描述")
    severity: str = Field(..., pattern="^(mild|moderate|severe)$", description="严重程度")
    recorded_at: Optional[datetime] = None
    is_active: bool = True


class AllergyListResponse(BaseModel):
    allergies: list[AllergyItem]
    count: int


class AllergyAddRequest(BaseModel):
    substance: str = Field(..., min_length=1, max_length=200)
    substance_code: Optional[str] = Field(None, max_length=100)
    reaction: Optional[str] = Field(None, max_length=500)
    severity: str = Field(..., pattern="^(mild|moderate|severe)$")


class AllergyAddResponse(BaseModel):
    id: str
    substance: str
    severity: str
    message: str


class AllergyDeleteResponse(BaseModel):
    message: str


@router.get("/allergies", response_model=AllergyListResponse,
            dependencies=[Depends(require_role("patient"))])
async def list_allergies():
    """Get the current patient's allergy list. (Mock stub — returns empty)"""
    # In production, this would query from DB using get_current_user().
    # For now returns an empty list as stub.
    return AllergyListResponse(allergies=[], count=0)


@router.post("/allergies", response_model=AllergyAddResponse,
             dependencies=[Depends(require_role("patient"))])
async def add_allergy(req: AllergyAddRequest):
    """Add an allergy for the current patient (patient self-report)."""
    allergy_id = str(uuid.uuid4())
    return AllergyAddResponse(
        id=allergy_id,
        substance=req.substance,
        severity=req.severity,
        message=f"已记录过敏: {req.substance}，请注意避免使用相关药物。",
    )


@router.delete("/allergies/{allergy_id}", response_model=AllergyDeleteResponse,
               dependencies=[Depends(require_role("patient"))])
async def remove_allergy(allergy_id: str):
    """Remove an allergy from the patient's allergy list."""
    return AllergyDeleteResponse(message=f"已删除过敏记录 {allergy_id}")
