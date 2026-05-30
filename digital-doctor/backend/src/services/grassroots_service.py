"""Grassroots service — patient cards, monthly reports, screening logic."""

import uuid
from datetime import datetime, date
from typing import Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.grassroots import (
    GrassrootsPatient,
    GrassrootsScreening,
    GrassrootsFollowUp,
    RiskLevel,
    ReferralStatus,
)


# ── Screening risk calculation ────────────────────────────────────────────

def calculate_screening_risk(
    age: int,
    waist_circumference: float,
    fasting_glucose: float,
    systolic_bp: int,
    diastolic_bp: int,
    family_history: bool,
) -> dict[str, Any]:
    """Calculate T2DM risk from grassroots screening fields.

    Returns risk level, score, and actionable recommendation.
    """
    scores: dict[str, int] = {}

    # Age scoring (simplified from standard risk model)
    if age < 35:
        scores["age"] = 0
    elif age < 45:
        scores["age"] = 2
    elif age < 55:
        scores["age"] = 4
    elif age < 65:
        scores["age"] = 6
    else:
        scores["age"] = 8

    # Waist circumference
    if waist_circumference < 85:
        scores["waist"] = 0
    elif waist_circumference < 95:
        scores["waist"] = 3
    else:
        scores["waist"] = 6

    # Fasting plasma glucose
    if fasting_glucose < 5.6:
        scores["glucose"] = 0
    elif fasting_glucose < 6.1:
        scores["glucose"] = 5
    elif fasting_glucose < 7.0:
        scores["glucose"] = 8
    else:
        scores["glucose"] = 12

    # Blood pressure
    if systolic_bp < 140 and diastolic_bp < 90:
        scores["bp"] = 0
    elif systolic_bp < 160 and diastolic_bp < 100:
        scores["bp"] = 2
    else:
        scores["bp"] = 4

    # Family history
    scores["family"] = 6 if family_history else 0

    total = sum(scores.values())

    risk_map = {range(0, 7): RiskLevel.LOW, range(7, 13): RiskLevel.MODERATE, range(13, 21): RiskLevel.HIGH}
    risk_level = RiskLevel.HIGH
    for rng, level in risk_map.items():
        if total <= rng.stop - 1:
            risk_level = level
            break
    if total >= 21:
        risk_level = RiskLevel.VERY_HIGH

    referral_needed = risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH) or fasting_glucose >= 7.0
    recommendation = _build_recommendation(risk_level, fasting_glucose, waist_circumference, systolic_bp, diastolic_bp)

    return {
        "risk_level": risk_level,
        "risk_score": total,
        "max_score": 36,
        "factor_scores": scores,
        "referral_needed": referral_needed,
        "recommendation": recommendation,
    }


def _build_recommendation(
    risk_level: RiskLevel,
    fpg: float,
    waist: float,
    sbp: int,
    dbp: int,
) -> str:
    parts = []
    if risk_level in (RiskLevel.HIGH, RiskLevel.VERY_HIGH):
        parts.append("高风险：建议转诊至上级医院内分泌科进一步检查")
    elif risk_level == RiskLevel.MODERATE:
        parts.append("中风险：建议3个月后复查空腹血糖")
    else:
        parts.append("低风险：保持健康生活方式")

    if fpg >= 7.0:
        parts.append("空腹血糖显著升高，需立即就医确认糖尿病诊断")
    elif fpg >= 6.1:
        parts.append("空腹血糖偏高，控制饮食碳水化合物摄入")
    if waist >= 90:
        parts.append("腹型肥胖，建议减重并增加运动")
    if sbp >= 140 or dbp >= 90:
        parts.append("血压偏高，低盐饮食并行血压监测")

    return "；".join(parts)


# ── Patient card generation ──────────────────────────────────────────────

async def generate_patient_card(
    gp_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Generate simplified patient card for community health workers."""
    stmt = select(GrassrootsPatient).where(GrassrootsPatient.id == gp_id)
    result = await db.execute(stmt)
    gp = result.scalar_one_or_none()
    if not gp:
        return None

    # Latest FPG from screenings
    latest_fpg_stmt = (
        select(GrassrootsScreening.fasting_glucose)
        .where(GrassrootsScreening.patient_id == gp.id)
        .order_by(desc(GrassrootsScreening.screened_at))
        .limit(1)
    )
    fpg_result = await db.execute(latest_fpg_stmt)
    latest_fpg = fpg_result.scalar()

    # Latest follow-up
    latest_fu_stmt = (
        select(GrassrootsFollowUp)
        .where(GrassrootsFollowUp.patient_id == gp.id)
        .order_by(desc(GrassrootsFollowUp.followed_up_at))
        .limit(1)
    )
    fu_result = await db.execute(latest_fu_stmt)
    latest_fu = fu_result.scalar_one_or_none()

    # Latest screening (for risk status)
    latest_screening_stmt = (
        select(GrassrootsScreening)
        .where(GrassrootsScreening.patient_id == gp.id)
        .order_by(desc(GrassrootsScreening.screened_at))
        .limit(1)
    )
    screening_result = await db.execute(latest_screening_stmt)
    latest_screening = screening_result.scalar_one_or_none()

    current_year = date.today().year
    age = current_year - gp.birth_year

    return {
        "id": str(gp.id),
        "name": gp.name,
        "age": age,
        "gender": "男" if gp.gender == "M" else "女",
        "village": gp.village,
        "diabetes_type": gp.diabetes_type or "未确诊",
        "latest_fpg": latest_fpg,
        "last_follow_up": latest_fu.followed_up_at.isoformat() if latest_fu else None,
        "risk_status": latest_screening.risk_level.value if latest_screening else "unknown",
        "referral_status": latest_screening.referral_status.value if latest_screening else "none",
        "next_follow_up": latest_fu.next_follow_up.isoformat() if latest_fu and latest_fu.next_follow_up else None,
    }


# ── Monthly report generation ────────────────────────────────────────────

async def generate_monthly_report(
    hospital_id: uuid.UUID | None,
    db: AsyncSession,
) -> dict[str, Any]:
    """Generate monthly statistical report for township health center."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    next_month = now.month + 1 if now.month < 12 else 1
    next_year = now.year if now.month < 12 else now.year + 1
    month_end = datetime(next_year, next_month, 1)

    # Base query — filter by hospital if provided
    patient_filter = [GrassrootsPatient.is_active == True]
    if hospital_id:
        patient_filter.append(GrassrootsPatient.hospital_id == hospital_id)

    # Total managed patients
    total_stmt = select(func.count()).select_from(GrassrootsPatient).where(*patient_filter)
    total_managed = (await db.execute(total_stmt)).scalar() or 0

    # Active screening patients (have a screening with risk high or above)
    high_risk_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.risk_level.in_([RiskLevel.HIGH, RiskLevel.VERY_HIGH]))
    )
    high_risk_count = (await db.execute(high_risk_stmt)).scalar() or 0

    # Screenings this month
    screenings_month_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.screened_at >= month_start)
        .where(GrassrootsScreening.screened_at < month_end)
    )
    screenings_this_month = (await db.execute(screenings_month_stmt)).scalar() or 0

    # New diagnoses this month (first screening in HIGH/VERY_HIGH)
    new_dx_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.risk_level.in_([RiskLevel.HIGH, RiskLevel.VERY_HIGH]))
        .where(GrassrootsScreening.screened_at >= month_start)
        .where(GrassrootsScreening.screened_at < month_end)
    )
    new_diagnoses = (await db.execute(new_dx_stmt)).scalar() or 0

    # Referral count
    referral_stmt = (
        select(func.count())
        .select_from(GrassrootsScreening)
        .join(GrassrootsPatient, GrassrootsScreening.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsScreening.referral_needed == True)
    )
    referral_count = (await db.execute(referral_stmt)).scalar() or 0

    # Follow-up completion rate (this month)
    fu_count_stmt = (
        select(func.count())
        .select_from(GrassrootsFollowUp)
        .join(GrassrootsPatient, GrassrootsFollowUp.patient_id == GrassrootsPatient.id)
        .where(*patient_filter)
        .where(GrassrootsFollowUp.followed_up_at >= month_start)
        .where(GrassrootsFollowUp.followed_up_at < month_end)
    )
    follow_ups_completed = (await db.execute(fu_count_stmt)).scalar() or 0

    # Due follow-ups (next_follow_up <= today and not yet done this month)
    today = date.today()
    overdue_stmt = (
        select(func.count())
        .select_from(GrassrootsPatient)
        .where(*patient_filter)
        .where(
            GrassrootsPatient.id.in_(
                select(GrassrootsFollowUp.patient_id).where(GrassrootsFollowUp.next_follow_up <= today)
            )
        )
    )
    overdue_follow_ups = (await db.execute(overdue_stmt)).scalar() or 0

    # Controlled rate — latest screening fasting glucose < 7.0
    controlled_count = 0
    if total_managed > 0:
        gp_ids_stmt = select(GrassrootsPatient.id).where(*patient_filter)
        gp_ids = (await db.execute(gp_ids_stmt)).scalars().all()
        for gpid in gp_ids:
            latest_s = (
                await db.execute(
                    select(GrassrootsScreening.fasting_glucose)
                    .where(GrassrootsScreening.patient_id == gpid)
                    .order_by(desc(GrassrootsScreening.screened_at))
                    .limit(1)
                )
            ).scalar()
            if latest_s is not None and latest_s < 7.0:
                controlled_count += 1

    controlled_rate = round(controlled_count / total_managed * 100, 1) if total_managed > 0 else 0

    return {
        "report_month": f"{now.year}-{now.month:02d}",
        "hospital_id": str(hospital_id) if hospital_id else None,
        "total_managed": total_managed,
        "high_risk_count": high_risk_count,
        "screenings_this_month": screenings_this_month,
        "new_diagnoses": new_diagnoses,
        "active_patients": total_managed,
        "controlled_rate": controlled_rate,
        "referral_count": referral_count,
        "follow_ups_completed": follow_ups_completed,
        "overdue_follow_ups": overdue_follow_ups,
        "follow_up_completion_rate": round(follow_ups_completed / (follow_ups_completed + overdue_follow_ups) * 100, 1)
        if (follow_ups_completed + overdue_follow_ups) > 0
        else 0,
    }
