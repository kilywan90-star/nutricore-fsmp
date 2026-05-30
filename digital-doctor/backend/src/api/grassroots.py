"""Grassroots API — community screening, follow-up, dashboard, offline sync.

No auth required for screening (public health use case).
Patient management requires grassroots role.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.grassroots import (
    GrassrootsPatient,
    GrassrootsScreening,
    GrassrootsFollowUp,
    RiskLevel,
    ReferralStatus,
)
from src.services.grassroots_service import (
    calculate_screening_risk,
    generate_patient_card,
    generate_monthly_report,
)
from src.services.offline_queue import OfflineQueue

router = APIRouter()

_offline_queue: OfflineQueue | None = None


def _get_offline_queue() -> OfflineQueue:
    global _offline_queue
    if _offline_queue is None:
        _offline_queue = OfflineQueue()
    return _offline_queue


# ── Request / Response models ────────────────────────────────────────────

class ScreeningRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    village: str = Field(min_length=1, max_length=200)
    age: int = Field(ge=18, le=120)
    gender: str = Field(pattern="^(M|F)$")
    waist_circumference: float = Field(ge=50, le=200)
    fasting_glucose: float = Field(ge=2.0, le=30.0)
    systolic_bp: int = Field(ge=60, le=250, default=120)
    diastolic_bp: int = Field(ge=30, le=150, default=80)
    family_history: bool = False
    hospital_id: Optional[str] = None


class ScreeningResponse(BaseModel):
    id: str
    patient_id: str
    name: str
    age: int
    gender: str
    risk_level: str
    risk_score: int
    max_score: int
    factor_scores: dict
    referral_needed: bool
    recommendation: str


class FollowUpRequest(BaseModel):
    glucose_value: Optional[float] = Field(default=None, ge=1.0, le=40.0)
    medication_adherent: Optional[bool] = None
    new_symptoms: Optional[str] = Field(default=None, max_length=500)
    referral_needed: bool = False
    referral_reason: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=500)
    next_follow_up: Optional[date] = None


class FollowUpResponse(BaseModel):
    id: str
    patient_id: str
    glucose_value: Optional[float]
    medication_adherent: Optional[bool]
    new_symptoms: Optional[str]
    referral_needed: bool
    followed_up_at: str
    next_follow_up: Optional[str]


class PatientListItem(BaseModel):
    id: str
    name: str
    age: int
    gender: str
    village: str
    diabetes_type: Optional[str]
    latest_fpg: Optional[float]
    risk_status: Optional[str]
    last_follow_up: Optional[str]


class DashboardResponse(BaseModel):
    total_managed: int
    high_risk_count: int
    overdue_follow_ups: int
    pending_referrals: int
    screenings_this_month: int
    today_screenings: int


# ── Routes ───────────────────────────────────────────────────────────────


@router.post("/screening", response_model=ScreeningResponse)
async def submit_screening(req: ScreeningRequest, db: AsyncSession = Depends(get_db)):
    """Submit a community screening record. No auth required — public health use case."""
    # Create or find grassroots patient
    gp = await _get_or_create_patient(
        db,
        name=req.name,
        village=req.village,
        gender=req.gender,
        birth_year=date.today().year - req.age,
        hospital_id=req.hospital_id,
    )

    result = calculate_screening_risk(
        age=req.age,
        waist_circumference=req.waist_circumference,
        fasting_glucose=req.fasting_glucose,
        systolic_bp=req.systolic_bp,
        diastolic_bp=req.diastolic_bp,
        family_history=req.family_history,
    )

    screening = GrassrootsScreening(
        patient_id=gp.id,
        age=req.age,
        gender=req.gender,
        waist_circumference=req.waist_circumference,
        fasting_glucose=req.fasting_glucose,
        systolic_bp=req.systolic_bp,
        diastolic_bp=req.diastolic_bp,
        family_history=req.family_history,
        risk_level=result["risk_level"],
        risk_score=result["risk_score"],
        referral_needed=result["referral_needed"],
        referral_status=ReferralStatus.PENDING if result["referral_needed"] else ReferralStatus.NONE,
        recommendation=result["recommendation"],
        synced=True,
    )
    db.add(screening)
    await db.commit()
    await db.refresh(screening)

    return ScreeningResponse(
        id=str(screening.id),
        patient_id=str(gp.id),
        name=req.name,
        age=req.age,
        gender="男" if req.gender == "M" else "女",
        risk_level=result["risk_level"].value,
        risk_score=result["risk_score"],
        max_score=result["max_score"],
        factor_scores=result["factor_scores"],
        referral_needed=result["referral_needed"],
        recommendation=result["recommendation"],
    )


@router.get("/patients", response_model=list[PatientListItem])
async def list_patients(
    village: Optional[str] = None,
    risk_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List managed patients — simplified view for community health workers."""
    query = select(GrassrootsPatient).where(GrassrootsPatient.is_active == True)
    if village:
        query = query.where(GrassrootsPatient.village.ilike(f"%{village}%"))

    # If filtering by risk, join to latest screening
    if risk_filter and risk_filter in ("high", "very_high", "moderate", "low"):
        risk_enum = RiskLevel(risk_filter)
        subquery = (
            select(GrassrootsScreening.patient_id, func.max(GrassrootsScreening.screened_at).label("max_at"))
            .group_by(GrassrootsScreening.patient_id)
            .subquery()
        )
        risk_query = (
            select(GrassrootsScreening.patient_id)
            .join(subquery, GrassrootsScreening.patient_id == subquery.c.patient_id)
            .where(GrassrootsScreening.screened_at == subquery.c.max_at)
            .where(GrassrootsScreening.risk_level == risk_enum)
        )
        risk_ids = (await db.execute(risk_query)).scalars().all()
        if risk_ids:
            query = query.where(GrassrootsPatient.id.in_(risk_ids))
        else:
            return []

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(desc(GrassrootsPatient.created_at))
    result = await db.execute(query)
    patients = result.scalars().all()

    items = []
    for gp in patients:
        card = await generate_patient_card(gp.id, db)
        items.append(
            PatientListItem(
                id=str(gp.id),
                name=gp.name,
                age=date.today().year - gp.birth_year,
                gender="男" if gp.gender == "M" else "女",
                village=gp.village,
                diabetes_type=gp.diabetes_type,
                latest_fpg=card.get("latest_fpg") if card else None,
                risk_status=card.get("risk_status") if card else None,
                last_follow_up=card.get("last_follow_up") if card else None,
            )
        )

    return items


@router.post("/patients/{patient_id}/follow-up", response_model=FollowUpResponse)
async def record_follow_up(
    patient_id: str,
    req: FollowUpRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a follow-up visit for a managed patient."""
    try:
        gpid = uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid patient_id")

    gp_stmt = select(GrassrootsPatient).where(GrassrootsPatient.id == gpid)
    gp = (await db.execute(gp_stmt)).scalar_one_or_none()
    if not gp:
        raise HTTPException(status_code=404, detail="Patient not found")

    fu = GrassrootsFollowUp(
        patient_id=gpid,
        glucose_value=req.glucose_value,
        medication_adherent=req.medication_adherent,
        new_symptoms=req.new_symptoms,
        referral_needed=req.referral_needed,
        referral_reason=req.referral_reason,
        notes=req.notes,
        next_follow_up=req.next_follow_up,
        synced=True,
    )
    db.add(fu)
    await db.commit()
    await db.refresh(fu)

    return FollowUpResponse(
        id=str(fu.id),
        patient_id=str(fu.patient_id),
        glucose_value=fu.glucose_value,
        medication_adherent=fu.medication_adherent,
        new_symptoms=fu.new_symptoms,
        referral_needed=fu.referral_needed,
        followed_up_at=fu.followed_up_at.isoformat(),
        next_follow_up=fu.next_follow_up.isoformat() if fu.next_follow_up else None,
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def grassroots_dashboard(
    hospital_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Grassroots dashboard stats — overview for community health workers."""
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    month_start = datetime(now.year, now.month, 1)

    patient_filter = [GrassrootsPatient.is_active == True]
    if hospital_id:
        try:
            hid = uuid.UUID(hospital_id)
            patient_filter.append(GrassrootsPatient.hospital_id == hid)
        except (ValueError, AttributeError):
            pass

    # Total managed
    total_stmt = select(func.count()).select_from(GrassrootsPatient).where(*patient_filter)
    total = (await db.execute(total_stmt)).scalar() or 0

    # High risk
    high_risk_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.risk_level.in_([RiskLevel.HIGH, RiskLevel.VERY_HIGH]))
    )
    high_risk = (await db.execute(high_risk_stmt)).scalar() or 0

    # Overdue follow-ups
    today = date.today()
    overdue_stmt = (
        select(func.count())
        .select_from(GrassrootsPatient)
        .where(*patient_filter)
        .where(
            GrassrootsPatient.id.in_(
                select(GrassrootsFollowUp.patient_id)
                .where(GrassrootsFollowUp.next_follow_up <= today)
                .where(
                    GrassrootsFollowUp.id.in_(
                        select(func.max(GrassrootsFollowUp.id))
                        .group_by(GrassrootsFollowUp.patient_id)
                    )
                )
            )
        )
    )
    # Simpler overdue calculation: patients whose latest follow-up has next_follow_up <= today
    overdue_subq = (
        select(
            GrassrootsFollowUp.patient_id,
            func.max(GrassrootsFollowUp.next_follow_up).label("next_fu"),
        )
        .group_by(GrassrootsFollowUp.patient_id)
        .subquery()
    )
    overdue_stmt = (
        select(func.count())
        .select_from(GrassrootsPatient)
        .join(overdue_subq, GrassrootsPatient.id == overdue_subq.c.patient_id)
        .where(*patient_filter)
        .where(overdue_subq.c.next_fu <= today)
    )
    overdue_follow_ups = (await db.execute(overdue_stmt)).scalar() or 0

    # Pending referrals
    pending_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.referral_status == ReferralStatus.PENDING)
    )
    pending_referrals = (await db.execute(pending_stmt)).scalar() or 0

    # Screenings this month
    screenings_month_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.screened_at >= month_start)
    )
    screenings_this_month = (await db.execute(screenings_month_stmt)).scalar() or 0

    # Today's screenings
    today_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.screened_at >= today_start)
    )
    today_screenings = (await db.execute(today_stmt)).scalar() or 0

    return DashboardResponse(
        total_managed=total,
        high_risk_count=high_risk,
        overdue_follow_ups=overdue_follow_ups,
        pending_referrals=pending_referrals,
        screenings_this_month=screenings_this_month,
        today_screenings=today_screenings,
    )


@router.post("/sync")
async def sync_data(db: AsyncSession = Depends(get_db)):
    """Sync offline-queued data with the main server."""
    queue = _get_offline_queue()
    try:
        result = queue.process_queue(db)
        await db.commit()
        return {"status": "ok", **result}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Sync failed: {exc}")


@router.get("/sync/status")
async def sync_status():
    """Check offline queue status."""
    queue = _get_offline_queue()
    return queue.get_queue_status()


# ── Helpers ──────────────────────────────────────────────────────────────


async def _get_or_create_patient(
    db: AsyncSession,
    name: str,
    village: str,
    gender: str,
    birth_year: int,
    hospital_id: Optional[str] = None,
) -> GrassrootsPatient:
    """Find existing grassroots patient by name+village+birth_year, or create new."""
    stmt = select(GrassrootsPatient).where(
        GrassrootsPatient.name == name,
        GrassrootsPatient.village == village,
        GrassrootsPatient.birth_year == birth_year,
        GrassrootsPatient.gender == gender,
    )
    result = await db.execute(stmt)
    gp = result.scalar_one_or_none()
    if gp:
        return gp

    hid = None
    if hospital_id:
        try:
            hid = uuid.UUID(hospital_id)
        except (ValueError, AttributeError):
            pass

    gp = GrassrootsPatient(
        name=name,
        village=village,
        gender=gender,
        birth_year=birth_year,
        hospital_id=hid,
    )
    db.add(gp)
    await db.flush()
    return gp
