"""Medical consortium API — referral management and remote consultation endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.db.session import get_db
from src.models.user import User
from src.api.auth_deps import require_role, get_current_user
from src.services.referral_engine import (
    evaluate_referral_need,
    find_referral_targets,
    create_referral,
    list_referrals,
    accept_referral,
)
from src.services.clinical_summary import generate_referral_summary
from src.services.remote_consultation import (
    prepare_consultation,
    create_consultation_session,
    record_consultation,
    list_consultations,
    get_consultation,
)

router = APIRouter()


# ── Request/Response models ──────────────────────────────────────────────

class EvaluateReferralRequest(BaseModel):
    hba1c: Optional[float] = None
    medication_count: int = 0
    egfr: Optional[float] = None
    has_active_foot_ulcer: bool = False
    recent_cvd_event: bool = False
    severe_hypoglycemia_episodes: int = 0
    is_pregnant: bool = False
    diabetes_type: str = "type2"


class CreateReferralRequest(BaseModel):
    patient_id: str
    from_hospital_id: str
    to_hospital_id: Optional[str] = None
    to_doctor_id: Optional[str] = None
    urgency: str = Field(default="routine", pattern="^(routine|urgent|emergency)$")
    target_department: str = "内分泌科"
    target_level: str = Field(default="county", pattern="^(county|municipal|provincial)$")
    reason: str = ""


class AcceptReferralRequest(BaseModel):
    accepted: bool = True


class SearchTargetsRequest(BaseModel):
    location: str = ""
    department: str = "内分泌科"
    level: str = Field(default="county", pattern="^(county|municipal|provincial)$")


class CreateConsultationRequest(BaseModel):
    patient_id: str
    clinical_question: str = Field(min_length=1, max_length=1000)
    consulting_doctor_id: Optional[str] = None
    consulting_hospital_id: Optional[str] = None


class CompleteConsultationRequest(BaseModel):
    notes: str = ""
    outcome: str = ""


# ── Referral endpoints ───────────────────────────────────────────────────


@router.post("/referrals/evaluate", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_evaluate_referral(req: EvaluateReferralRequest):
    """Evaluate whether a patient needs referral based on clinical criteria."""
    patient_data = {
        "hba1c": req.hba1c,
        "medication_count": req.medication_count,
        "egfr": req.egfr,
        "has_active_foot_ulcer": req.has_active_foot_ulcer,
        "recent_cvd_event": req.recent_cvd_event,
        "severe_hypoglycemia_episodes": req.severe_hypoglycemia_episodes,
        "is_pregnant": req.is_pregnant,
        "diabetes_type": req.diabetes_type,
    }
    complication_risks = {}  # Will be integrated with risk calculators later
    return evaluate_referral_need(patient_data, complication_risks)


@router.post("/referrals/search-targets", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_search_targets(
    req: SearchTargetsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Find available hospitals in the consortium for a referral target."""
    return await find_referral_targets(
        patient_location=req.location,
        needed_department=req.department,
        target_level=req.level,
        db=db,
    )


@router.post("/referrals/create", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_create_referral(
    req: CreateReferralRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a referral with auto-generated clinical summary."""
    try:
        patient_uid = uuid.UUID(req.patient_id)
        from_hid = uuid.UUID(req.from_hospital_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    to_hid = uuid.UUID(req.to_hospital_id) if req.to_hospital_id else None
    to_did = uuid.UUID(req.to_doctor_id) if req.to_doctor_id else None

    # Generate clinical summary
    try:
        clinical_summary = await generate_referral_summary(patient_uid, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        result = await create_referral(
            patient_id=patient_uid,
            from_hospital_id=from_hid,
            from_doctor_id=user.id,
            to_hospital_id=to_hid,
            to_doctor_id=to_did,
            urgency=req.urgency,
            target_department=req.target_department,
            target_level=req.target_level,
            reason=req.reason,
            clinical_summary=clinical_summary,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.get("/referrals", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_list_referrals(
    hospital_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List referrals, scoped to the requesting doctor or hospital."""
    hid = uuid.UUID(hospital_id) if hospital_id else None
    return await list_referrals(
        db=db,
        hospital_id=hid,
        doctor_id=user.id,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.put("/referrals/{referral_id}/accept", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_accept_referral(
    referral_id: str,
    req: AcceptReferralRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept or reject an incoming referral."""
    try:
        rid = uuid.UUID(referral_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid referral_id")

    if not req.accepted:
        raise HTTPException(status_code=400, detail="Rejection not yet implemented; set accepted=true")

    try:
        result = await accept_referral(db=db, referral_id=rid, acceptor_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.get("/referrals/{referral_id}/summary", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_get_referral_summary(
    referral_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the clinical summary for a specific referral."""
    from src.models.org import ReferralRecord
    from sqlalchemy import select

    try:
        rid = uuid.UUID(referral_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid referral_id")

    stmt = select(ReferralRecord).where(ReferralRecord.id == rid)
    result = await db.execute(stmt)
    referral = result.scalar_one_or_none()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    return {
        "referral_id": str(referral.id),
        "clinical_summary": referral.clinical_summary,
    }


# ── Consultation endpoints ───────────────────────────────────────────────


@router.post("/consultations", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_create_consultation(
    req: CreateConsultationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Request a remote consultation with AI-prepared case materials."""
    try:
        patient_uid = uuid.UUID(req.patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    cons_doc = uuid.UUID(req.consulting_doctor_id) if req.consulting_doctor_id else None
    cons_hosp = uuid.UUID(req.consulting_hospital_id) if req.consulting_hospital_id else None

    try:
        result = await create_consultation_session(
            patient_id=patient_uid,
            requesting_doctor_id=user.id,
            clinical_question=req.clinical_question,
            consulting_doctor_id=cons_doc,
            consulting_hospital_id=cons_hosp,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@router.get("/consultations", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_list_consultations(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List consultation sessions for the requesting doctor."""
    return await list_consultations(
        db=db,
        doctor_id=user.id,
        status_filter=status,
        page=page,
        page_size=page_size,
    )


@router.get("/consultations/{session_id}", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_get_consultation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single consultation session."""
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid session_id")

    try:
        result = await get_consultation(sid, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@router.post("/consultations/{session_id}/complete", dependencies=[Depends(require_role("doctor", "department_head", "admin"))])
async def api_complete_consultation(
    session_id: str,
    req: CompleteConsultationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Complete a consultation with notes and outcome."""
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid session_id")

    try:
        result = await record_consultation(
            session_id=sid,
            notes=req.notes,
            outcome=req.outcome,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result
