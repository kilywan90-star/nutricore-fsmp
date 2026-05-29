import uuid
from typing import Any
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.patient import Patient, GlucoseRecord
from src.models.clinical import LabReport, Alert


async def get_patient_list(
    db: AsyncSession,
    doctor_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    risk_filter: str | None = None,
) -> dict[str, Any]:
    query = select(Patient)
    if search:
        query = query.where(Patient.name_hash.ilike(f"%{search}%"))
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(desc(Patient.created_at))
    result = await db.execute(query)
    patients = result.scalars().all()
    items = []
    for p in patients:
        latest_glucose = await _get_latest_glucose(db, p.id)
        alert_count = await _get_unacknowledged_alert_count(db, p.id)
        items.append({
            "id": str(p.id),
            "gender": p.gender,
            "birth_year": p.birth_year,
            "diabetes_type": p.diabetes_type,
            "hba1c_target": p.hba1c_target,
            "latest_glucose": latest_glucose,
            "alert_count": alert_count,
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


async def _get_latest_glucose(db: AsyncSession, patient_id) -> float | None:
    stmt = (
        select(GlucoseRecord.value_mmol_l)
        .where(GlucoseRecord.patient_id == patient_id)
        .order_by(desc(GlucoseRecord.recorded_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    val = result.scalar()
    return round(val, 1) if val else None


async def _get_unacknowledged_alert_count(db: AsyncSession, patient_id) -> int:
    stmt = select(func.count()).where(
        Alert.patient_id == patient_id,
        Alert.acknowledged == False,
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


def _parse_uuid(patient_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(patient_id)
    except (ValueError, AttributeError):
        return uuid.UUID("00000000-0000-0000-0000-000000000000")


async def get_patient_detail(db: AsyncSession, patient_id: str) -> dict | None:
    uid = _parse_uuid(patient_id)
    stmt = select(Patient).where(Patient.id == uid)
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()
    if not patient:
        return None

    glucose_stmt = (
        select(GlucoseRecord)
        .where(GlucoseRecord.patient_id == patient.id)
        .order_by(desc(GlucoseRecord.recorded_at))
        .limit(90)
    )
    glucose_result = await db.execute(glucose_stmt)
    glucose_records = glucose_result.scalars().all()

    lab_stmt = (
        select(LabReport)
        .where(LabReport.patient_id == patient.id)
        .order_by(desc(LabReport.report_date))
        .limit(10)
    )
    lab_result = await db.execute(lab_stmt)
    lab_reports = lab_result.scalars().all()

    alert_stmt = (
        select(Alert)
        .where(Alert.patient_id == patient.id)
        .order_by(desc(Alert.created_at))
        .limit(20)
    )
    alert_result = await db.execute(alert_stmt)
    alerts = alert_result.scalars().all()

    return {
        "id": str(patient.id),
        "gender": patient.gender,
        "birth_year": patient.birth_year,
        "diabetes_type": patient.diabetes_type,
        "diagnosis_date": patient.diagnosis_date.isoformat() if patient.diagnosis_date else None,
        "hba1c_target": patient.hba1c_target,
        "glucose_records": [
            {
                "id": str(g.id),
                "value_mmol_l": g.value_mmol_l,
                "measure_type": g.measure_type,
                "recorded_at": g.recorded_at.isoformat(),
                "notes": g.notes,
            }
            for g in glucose_records
        ],
        "lab_reports": [
            {
                "id": str(l.id),
                "report_type": l.report_type,
                "report_date": l.report_date.isoformat(),
                "results": l.results,
                "ai_interpretation": l.ai_interpretation,
            }
            for l in lab_reports
        ],
        "alerts": [
            {
                "id": str(a.id),
                "alert_type": a.alert_type,
                "severity": a.severity.value,
                "title": a.title,
                "detail": a.detail,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }
