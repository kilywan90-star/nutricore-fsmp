"""Referral engine — evaluates referral need, finds targets, and creates referrals.

Criteria based on Chinese T2DM guidelines and clinical practice:
  - HbA1c > 9.0% despite 3+ medications
  - eGFR < 30 (Stage 4+ CKD)
  - Active foot ulcer (Wagner grade >= 2)
  - CVD event within 6 months
  - Severe hypoglycemia episodes (requiring assistance)
  - Pregnancy + diabetes (gestational or pre-existing)
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.org import (
    Hospital,
    Department,
    DoctorProfile,
    ReferralRecord,
    ReferralUrgency,
    ReferralStatus,
    ReferralTargetLevel,
)


def evaluate_referral_need(
    patient_data: dict,
    complication_risks: dict,
) -> dict[str, Any]:
    """Determine if a patient needs referral based on clinical criteria.

    Args:
        patient_data: {
            hba1c: float | None,
            medication_count: int,
            egfr: float | None,
            has_active_foot_ulcer: bool,
            recent_cvd_event: bool,
            severe_hypoglycemia_episodes: int,
            is_pregnant: bool,
            diabetes_type: str,
        }
        complication_risks: {
            nephropathy_risk: str,
            retinopathy_risk: str,
            cvd_risk: str,
            foot_risk: str,
        }

    Returns:
        {referral_needed, urgency, target_department, target_level, reason}
    """
    reasons: list[str] = []
    urgency = ReferralUrgency.ROUTINE
    target_level = ReferralTargetLevel.COUNTY
    target_department = "内分泌科"

    hba1c = patient_data.get("hba1c")
    med_count = patient_data.get("medication_count", 0)
    egfr = patient_data.get("egfr")
    has_ulcer = patient_data.get("has_active_foot_ulcer", False)
    recent_cvd = patient_data.get("recent_cvd_event", False)
    hypo_episodes = patient_data.get("severe_hypoglycemia_episodes", 0)
    is_pregnant = patient_data.get("is_pregnant", False)
    has_diabetes = True  # Always True in this context

    # Emergency criteria — any one of these = emergency referral
    if recent_cvd:
        reasons.append("近6个月内心血管事件")
        urgency = ReferralUrgency.EMERGENCY
        target_department = "心血管内科"
        target_level = ReferralTargetLevel.PROVINCIAL

    if egfr is not None and egfr < 30:
        reasons.append(f"eGFR严重下降至{egfr:.0f} mL/min/1.73m²")
        if urgency != ReferralUrgency.EMERGENCY:
            urgency = ReferralUrgency.URGENT
        target_department = _resolve_department(["肾内科", "内分泌科"], target_department)
        target_level = _max_level(target_level, ReferralTargetLevel.MUNICIPAL)

    if has_ulcer:
        reasons.append("活动性糖尿病足溃疡")
        if urgency != ReferralUrgency.EMERGENCY:
            urgency = ReferralUrgency.URGENT
        target_department = _resolve_department(["内分泌科", "血管外科"], target_department)
        target_level = _max_level(target_level, ReferralTargetLevel.MUNICIPAL)

    if hypo_episodes >= 2:
        reasons.append(f"严重低血糖反复发作({hypo_episodes}次)")
        if urgency == ReferralUrgency.ROUTINE:
            urgency = ReferralUrgency.URGENT
        target_level = _max_level(target_level, ReferralTargetLevel.MUNICIPAL)

    if hba1c is not None and hba1c > 9.0 and med_count >= 3:
        reasons.append(f"HbA1c {hba1c}%持续不达标，已使用{med_count}种降糖药物")
        if urgency == ReferralUrgency.ROUTINE:
            urgency = ReferralUrgency.ROUTINE
        target_level = _max_level(target_level, ReferralTargetLevel.MUNICIPAL)

    if is_pregnant and has_diabetes:
        reasons.append("妊娠合并糖尿病")
        if urgency == ReferralUrgency.ROUTINE:
            urgency = ReferralUrgency.URGENT
        target_department = "妇产科"
        target_level = _max_level(target_level, ReferralTargetLevel.MUNICIPAL)

    # Check complication risks for additional reasons
    cvd_risk = complication_risks.get("cvd_risk", "")
    nephro_risk = complication_risks.get("nephropathy_risk", "")
    foot_risk = complication_risks.get("foot_risk", "")

    if cvd_risk in ("high", "极高危") and not recent_cvd:
        reasons.append("心血管疾病高风险")
        target_department = _resolve_department(["心血管内科", target_department], target_department)

    if nephro_risk in ("high", "极高危") and (egfr is None or egfr >= 30):
        reasons.append("糖尿病肾病高风险")

    if foot_risk in ("high", "极高危") and not has_ulcer:
        reasons.append("糖尿病足高风险")

    referral_needed = len(reasons) > 0
    reason_text = "；".join(reasons) if reasons else "暂无转诊指征"

    return {
        "referral_needed": referral_needed,
        "urgency": urgency.value,
        "target_department": target_department,
        "target_level": target_level.value,
        "reason": reason_text,
        "criteria_met": len(reasons),
    }


async def find_referral_targets(
    patient_location: str,
    needed_department: str,
    target_level: str,
    db: AsyncSession,
) -> list[dict[str, Any]]:
    """Search available hospitals in the consortium network matching criteria.

    Args:
        patient_location: City or county name for proximity matching
        needed_department: Target department name
        target_level: Minimum hospital level (county/municipal/provincial)
        db: Database session
    """
    from src.models.org import HospitalLevel

    level_map = {
        "county": ["一级甲等", "二级乙等", "二级甲等", "三级乙等", "三级甲等"],
        "municipal": ["二级甲等", "三级乙等", "三级甲等"],
        "provincial": ["三级乙等", "三级甲等"],
    }
    allowed_levels = level_map.get(target_level, level_map["county"])

    # Find hospitals with matching department and level
    dept_query = (
        select(Department)
        .join(Hospital, Department.hospital_id == Hospital.id)
        .where(
            Department.name.ilike(f"%{needed_department}%"),
            Department.is_active == True,
            Hospital.is_active == True,
            Hospital.level.in_([HospitalLevel(lv) for lv in allowed_levels]),
        )
        .order_by(Hospital.level.desc())
        .limit(20)
    )
    result = await db.execute(dept_query)
    departments = result.scalars().all()

    seen_hospitals: set[uuid.UUID] = set()
    targets: list[dict[str, Any]] = []

    for dept in departments:
        if dept.hospital_id in seen_hospitals:
            continue
        seen_hospitals.add(dept.hospital_id)

        # Resolve hospital
        hosp_stmt = select(Hospital).where(Hospital.id == dept.hospital_id)
        hosp_result = await db.execute(hosp_stmt)
        hospital = hosp_result.scalar_one_or_none()
        if not hospital:
            continue

        # Count available doctors in target department
        from sqlalchemy import func

        doc_count_stmt = (
            select(func.count())
            .select_from(DoctorProfile)
            .where(
                DoctorProfile.department_id == dept.id,
                DoctorProfile.hospital_id == hospital.id,
                DoctorProfile.is_active == True,
            )
        )
        doctor_count = (await db.execute(doc_count_stmt)).scalar() or 0

        targets.append({
            "id": str(hospital.id),
            "name": hospital.name,
            "code": hospital.code,
            "address": hospital.address,
            "level": hospital.level.value if hospital.level else None,
            "department_id": str(dept.id),
            "department_name": dept.name,
            "doctor_count": doctor_count,
        })

    return targets


async def create_referral(
    patient_id: uuid.UUID,
    from_hospital_id: uuid.UUID,
    from_doctor_id: uuid.UUID,
    clinical_summary: dict[str, Any],
    db: AsyncSession,
    to_hospital_id: uuid.UUID | None = None,
    to_doctor_id: uuid.UUID | None = None,
    urgency: str = "routine",
    target_department: str = "内分泌科",
    target_level: str = "county",
    reason: str = "",
) -> dict[str, Any]:
    """Create a referral record with structured clinical summary.

    Args:
        patient_id: Patient UUID
        from_hospital_id: Referring hospital UUID
        from_doctor_id: Referring doctor UUID
        clinical_summary: Pre-generated clinical summary dict
        db: Database session
        to_hospital_id: Target hospital UUID (optional at creation)
        to_doctor_id: Target doctor UUID (optional)
        urgency: Referral urgency level
        target_department: Target department
        target_level: Required hospital level
        reason: Reason for referral

    Returns:
        Created referral dict
    """
    if from_hospital_id == to_hospital_id:
        raise ValueError("Cannot refer to the same hospital. Use internal consult instead.")

    # Verify source hospital exists and is active
    from_hosp_stmt = select(Hospital).where(
        Hospital.id == from_hospital_id,
        Hospital.is_active == True,
    )
    from_hosp = (await db.execute(from_hosp_stmt)).scalar_one_or_none()
    if not from_hosp:
        raise ValueError(f"Source hospital not found or inactive: {from_hospital_id}")

    # Verify target hospital if specified
    to_hosp_name: str | None = None
    if to_hospital_id:
        to_hosp_stmt = select(Hospital).where(
            Hospital.id == to_hospital_id,
            Hospital.is_active == True,
        )
        to_hosp = (await db.execute(to_hosp_stmt)).scalar_one_or_none()
        if not to_hosp:
            raise ValueError(f"Target hospital not found or inactive: {to_hospital_id}")
        to_hosp_name = to_hosp.name

    referral = ReferralRecord(
        patient_id=patient_id,
        from_hospital_id=from_hospital_id,
        from_doctor_id=from_doctor_id,
        to_hospital_id=to_hospital_id,
        to_doctor_id=to_doctor_id,
        target_department=target_department,
        urgency=ReferralUrgency(urgency),
        target_level=ReferralTargetLevel(target_level),
        clinical_summary=clinical_summary,
        reason=reason,
        status=ReferralStatus.PENDING,
    )
    db.add(referral)
    await db.commit()
    await db.refresh(referral)

    return {
        "id": str(referral.id),
        "patient_id": str(referral.patient_id),
        "from_hospital_id": str(referral.from_hospital_id),
        "from_hospital_name": from_hosp.name,
        "from_doctor_id": str(referral.from_doctor_id),
        "to_hospital_id": str(referral.to_hospital_id) if referral.to_hospital_id else None,
        "to_hospital_name": to_hosp_name,
        "to_doctor_id": str(referral.to_doctor_id) if referral.to_doctor_id else None,
        "target_department": referral.target_department,
        "urgency": referral.urgency.value,
        "target_level": referral.target_level.value,
        "clinical_summary": clinical_summary,
        "reason": referral.reason,
        "status": referral.status.value,
        "created_at": referral.created_at.isoformat(),
    }


async def list_referrals(
    db: AsyncSession,
    hospital_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List referral records with optional filters."""
    from sqlalchemy import func

    query = select(ReferralRecord)
    if hospital_id:
        query = query.where(
            (ReferralRecord.from_hospital_id == hospital_id)
            | (ReferralRecord.to_hospital_id == hospital_id)
        )
    if doctor_id:
        query = query.where(
            (ReferralRecord.from_doctor_id == doctor_id)
            | (ReferralRecord.to_doctor_id == doctor_id)
        )
    if status_filter:
        query = query.where(ReferralRecord.status == ReferralStatus(status_filter))

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    query = query.order_by(desc(ReferralRecord.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    referrals = result.scalars().all()

    items = []
    for r in referrals:
        from_hosp = (await db.execute(select(Hospital).where(Hospital.id == r.from_hospital_id))).scalar_one_or_none()
        to_hosp = (await db.execute(select(Hospital).where(Hospital.id == r.to_hospital_id))).scalar_one_or_none() if r.to_hospital_id else None

        items.append({
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "from_hospital_id": str(r.from_hospital_id),
            "from_hospital_name": from_hosp.name if from_hosp else "",
            "from_doctor_id": str(r.from_doctor_id),
            "to_hospital_id": str(r.to_hospital_id) if r.to_hospital_id else None,
            "to_hospital_name": to_hosp.name if to_hosp else None,
            "to_doctor_id": str(r.to_doctor_id) if r.to_doctor_id else None,
            "target_department": r.target_department,
            "urgency": r.urgency.value,
            "target_level": r.target_level.value,
            "reason": r.reason,
            "status": r.status.value,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def accept_referral(
    db: AsyncSession,
    referral_id: uuid.UUID,
    acceptor_id: uuid.UUID,
) -> dict[str, Any]:
    """Accept an incoming referral."""
    stmt = select(ReferralRecord).where(ReferralRecord.id == referral_id)
    result = await db.execute(stmt)
    referral = result.scalar_one_or_none()
    if not referral:
        raise ValueError(f"Referral not found: {referral_id}")
    if referral.status != ReferralStatus.PENDING:
        raise ValueError(f"Referral is not pending: {referral.status.value}")

    referral.status = ReferralStatus.ACCEPTED
    referral.to_doctor_id = acceptor_id
    referral.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(referral)

    return {
        "id": str(referral.id),
        "status": referral.status.value,
        "to_doctor_id": str(acceptor_id),
        "updated_at": referral.updated_at.isoformat() if referral.updated_at else None,
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_department(candidates: list[str], fallback: str) -> str:
    """Pick the first candidate department; append fallback if none match."""
    return candidates[0]


def _max_level(a: ReferralTargetLevel, b: ReferralTargetLevel) -> ReferralTargetLevel:
    level_order = {
        ReferralTargetLevel.COUNTY: 1,
        ReferralTargetLevel.MUNICIPAL: 2,
        ReferralTargetLevel.PROVINCIAL: 3,
    }
    return a if level_order[a] >= level_order[b] else b
