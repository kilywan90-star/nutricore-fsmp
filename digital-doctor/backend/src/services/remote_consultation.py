"""Remote consultation service — AI-assisted case preparation and consultation management.

Supports cross-hospital remote consultations within the medical consortium:
  - AI prepares case summaries + relevant guidelines for consulting physicians
  - Tracks consultation lifecycle: requested → accepted → in_progress → completed
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.org import (
    ConsultationSession,
    ConsultationStatus,
    Hospital,
    Department,
    DoctorProfile,
)
from src.models.patient import Patient
from src.models.clinical import LabReport, Alert
from src.services.clinical_summary import generate_referral_summary


async def prepare_consultation(
    patient_id: uuid.UUID,
    clinical_question: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Prepare AI-assisted case materials for a remote consultation.

    Generates:
      - Full clinical summary via the referral summary generator
      - Relevant guideline excerpts based on the clinical question
      - Suggested differentials based on patient data + question context

    Args:
        patient_id: Patient UUID
        clinical_question: Question posed by the requesting physician
        db: Database session

    Returns:
        Prepared consultation materials dict
    """
    # Generate full clinical summary
    clinical_summary = await generate_referral_summary(patient_id, db)

    # Extract patient info for context
    patient_stmt = select(Patient).where(Patient.id == patient_id)
    patient = (await db.execute(patient_stmt)).scalar_one_or_none()
    if not patient:
        raise ValueError(f"Patient not found: {patient_id}")

    # Generate relevant guidelines based on clinical question keywords
    relevant_guidelines = _match_guidelines(clinical_question, clinical_summary)

    # Suggest differentials based on clinical context
    suggested_differentials = _suggest_differentials(
        clinical_question,
        clinical_summary,
        patient.diabetes_type,
    )

    return {
        "clinical_summary": clinical_summary,
        "clinical_question": clinical_question,
        "relevant_guidelines": relevant_guidelines,
        "suggested_differentials": suggested_differentials,
        "prepared_at": datetime.utcnow().isoformat(),
    }


async def create_consultation_session(
    patient_id: uuid.UUID,
    requesting_doctor_id: uuid.UUID,
    clinical_question: str,
    db: AsyncSession,
    consulting_doctor_id: uuid.UUID | None = None,
    consulting_hospital_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Create a new remote consultation session.

    Args:
        patient_id: Patient UUID
        requesting_doctor_id: Doctor requesting the consultation
        clinical_question: Clinical question for the consultant
        db: Database session
        consulting_doctor_id: Target consultant (optional)
        consulting_hospital_id: Target hospital (optional)

    Returns:
        Created consultation session dict
    """
    # Auto-prepare AI summary
    ai_summary = await prepare_consultation(patient_id, clinical_question, db)

    session = ConsultationSession(
        patient_id=patient_id,
        requesting_doctor_id=requesting_doctor_id,
        consulting_doctor_id=consulting_doctor_id,
        consulting_hospital_id=consulting_hospital_id,
        status=ConsultationStatus.REQUESTED,
        clinical_question=clinical_question,
        ai_prepared_summary=ai_summary,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return _serialize_session(session)


async def record_consultation(
    session_id: uuid.UUID,
    db: AsyncSession,
    notes: str = "",
    outcome: str = "",
) -> dict[str, Any]:
    """Record consultation notes and/or outcome, marking as completed if outcome provided.

    Args:
        session_id: Consultation session UUID
        db: Database session
        notes: Consultation notes/discussion
        outcome: Consultation outcome/conclusion

    Returns:
        Updated consultation session dict
    """
    stmt = select(ConsultationSession).where(ConsultationSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Consultation session not found: {session_id}")

    if notes:
        session.consultation_notes = notes
    if outcome:
        session.outcome = outcome
        session.status = ConsultationStatus.COMPLETED
        session.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    return _serialize_session(session)


async def list_consultations(
    db: AsyncSession,
    doctor_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List consultation sessions, optionally filtered by doctor and status."""
    from sqlalchemy import func

    query = select(ConsultationSession)
    if doctor_id:
        query = query.where(
            (ConsultationSession.requesting_doctor_id == doctor_id)
            | (ConsultationSession.consulting_doctor_id == doctor_id)
        )
    if status_filter:
        query = query.where(ConsultationSession.status == ConsultationStatus(status_filter))

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    query = query.order_by(desc(ConsultationSession.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    sessions = result.scalars().all()

    items = [_serialize_session(s) for s in sessions]

    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def get_consultation(
    session_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Get a single consultation session by ID."""
    stmt = select(ConsultationSession).where(ConsultationSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"Consultation session not found: {session_id}")
    return _serialize_session(session)


def _serialize_session(session: ConsultationSession) -> dict[str, Any]:
    """Serialize a ConsultationSession to a JSON-safe dict."""
    return {
        "id": str(session.id),
        "patient_id": str(session.patient_id),
        "requesting_doctor_id": str(session.requesting_doctor_id),
        "consulting_doctor_id": str(session.consulting_doctor_id) if session.consulting_doctor_id else None,
        "consulting_hospital_id": str(session.consulting_hospital_id) if session.consulting_hospital_id else None,
        "status": session.status.value,
        "clinical_question": session.clinical_question,
        "ai_prepared_summary": session.ai_prepared_summary,
        "consultation_notes": session.consultation_notes,
        "outcome": session.outcome,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


def _match_guidelines(question: str, summary: dict) -> list[dict[str, str]]:
    """Match relevant clinical guidelines based on question keywords."""
    guidelines_db = {
        "血糖": {"title": "中国2型糖尿病防治指南(2024版) - 血糖控制目标", "section": "血糖控制"},
        "胰岛素": {"title": "中国2型糖尿病防治指南(2024版) - 胰岛素治疗", "section": "胰岛素治疗路径"},
        "并发症": {"title": "中国2型糖尿病防治指南(2024版) - 慢性并发症筛查", "section": "并发症管理"},
        "肾病": {"title": "中国糖尿病肾脏病防治指南(2023版)", "section": "DKD筛查与治疗"},
        "足": {"title": "中国糖尿病足防治指南(2024版)", "section": "足病分级与处理"},
        "妊娠": {"title": "妊娠期高血糖诊治指南(2022版)", "section": "妊娠期血糖管理"},
        "低血糖": {"title": "中国2型糖尿病防治指南(2024版) - 低血糖管理", "section": "低血糖防治"},
        "心血管": {"title": "中国2型糖尿病防治指南(2024版) - 心血管风险管理", "section": "ASCVD风险评估"},
        "高血压": {"title": "中国高血压防治指南(2023版)", "section": "糖尿病合并高血压"},
    }

    matched: list[dict[str, str]] = []
    seen: set[str] = set()
    for keyword, guideline in guidelines_db.items():
        if keyword in question and guideline["section"] not in seen:
            matched.append(guideline)
            seen.add(guideline["section"])

    # Always include the core diabetes guideline
    core = {"title": "中国2型糖尿病防治指南(2024版)", "section": "综合管理"}
    if core["section"] not in seen:
        matched.insert(0, core)

    return matched[:5]


def _suggest_differentials(
    question: str,
    summary: dict,
    diabetes_type: str,
) -> list[str]:
    """Suggest differential diagnoses based on clinical context."""
    differentials: list[str] = []
    glucose = summary.get("glucose_control_summary", {})
    complications = summary.get("complication_status", {})
    comp_details = complications.get("details", {})

    avg_glucose = glucose.get("avg_mmol_l")
    if avg_glucose and avg_glucose > 11.0:
        differentials.append("除外糖尿病酮症酸中毒（DKA）或高渗性高血糖状态（HHS）")

    if "hypoglycemia" in comp_details:
        differentials.append("评估低血糖原因：药物过量/进食不足/肝肾功异常/胰岛素瘤")

    if "foot" in comp_details:
        differentials.append("评估糖尿病足感染程度及骨髓炎可能")

    if "nephropathy" in comp_details:
        differentials.append("评估是否存在非糖尿病性肾损害（如药物性、肾小球肾炎）")

    if "retinopathy" in comp_details:
        differentials.append("需除外其他原因导致的视网膜病变（如高血压性、老年性黄斑变性）")

    if "cvd" in comp_details:
        differentials.append("心血管事件风险分层及进一步检查（冠状动脉CTA、心脏超声）")

    # Diabetes type-specific
    if diabetes_type == "type1":
        differentials.append("评估胰岛功能，排除LADA或MODY可能")
    elif diabetes_type == "type2":
        differentials.append("评估是否存在继发性糖尿病（如胰腺疾病、内分泌疾病）")

    if not differentials:
        differentials.append("目前无特殊鉴别诊断提示，建议根据临床检查进一步评估")

    return differentials[:5]
