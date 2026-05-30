"""Clinical summary generator — auto-generates structured referral documents.

Produces a comprehensive clinical summary suitable for handoff to receiving
physicians within the medical consortium.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.patient import Patient, GlucoseRecord, MedicationReminder
from src.models.clinical import LabReport, Alert


async def generate_referral_summary(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """Auto-generate a structured clinical summary for referral handoff.

    Returns a dict containing:
      - patient_demographics
      - current_medications
      - recent_lab_results (last 3 months)
      - glucose_control_summary
      - complication_status
      - reason_for_referral (placeholder; caller fills actual reason)
      - questions_for_receiving_physician
    """
    patient_stmt = select(Patient).where(Patient.id == patient_id)
    patient = (await db.execute(patient_stmt)).scalar_one_or_none()
    if not patient:
        raise ValueError(f"Patient not found: {patient_id}")

    # ── Patient demographics ──────────────────────────────────────────────
    age = datetime.utcnow().year - patient.birth_year
    duration_years: float | None = None
    if patient.diagnosis_date:
        duration_years = round(
            (datetime.utcnow().date() - patient.diagnosis_date).days / 365.25, 1
        )

    demographics = {
        "age": age,
        "gender": patient.gender,
        "birth_year": patient.birth_year,
        "diabetes_type": patient.diabetes_type,
        "duration_years": duration_years,
        "diagnosis_date": patient.diagnosis_date.isoformat() if patient.diagnosis_date else None,
    }

    # ── Current medications ───────────────────────────────────────────────
    med_stmt = (
        select(MedicationReminder)
        .where(
            MedicationReminder.patient_id == patient_id,
            MedicationReminder.is_active == True,
        )
        .order_by(MedicationReminder.start_date.desc())
    )
    med_result = await db.execute(med_stmt)
    medications = med_result.scalars().all()

    current_medications = [
        {
            "drug_name": m.drug_name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "time_of_day": m.time_of_day,
            "start_date": m.start_date.isoformat() if m.start_date else None,
        }
        for m in medications
    ]

    # ── Recent lab results (last 3 months) ────────────────────────────────
    from datetime import timedelta

    three_months_ago = datetime.utcnow().date() - timedelta(days=90)
    lab_stmt = (
        select(LabReport)
        .where(
            LabReport.patient_id == patient_id,
            LabReport.report_date >= three_months_ago,
        )
        .order_by(desc(LabReport.report_date))
    )
    lab_result = await db.execute(lab_stmt)
    lab_reports = lab_result.scalars().all()

    recent_labs = [
        {
            "report_type": lr.report_type,
            "report_date": lr.report_date.isoformat() if lr.report_date else None,
            "results": lr.results,
            "ai_interpretation": lr.ai_interpretation,
        }
        for lr in lab_reports
    ]

    # Extract HbA1c history from lab results
    hba1c_history: list[dict[str, Any]] = []
    for lr in lab_reports:
        if lr.results and "hba1c" in lr.results:
            hba1c_history.append({
                "date": lr.report_date.isoformat() if lr.report_date else None,
                "value": lr.results["hba1c"],
            })

    # ── Glucose control summary ───────────────────────────────────────────
    glucose_stmt = (
        select(GlucoseRecord)
        .where(GlucoseRecord.patient_id == patient_id)
        .order_by(desc(GlucoseRecord.recorded_at))
        .limit(100)
    )
    glucose_result = await db.execute(glucose_stmt)
    glucose_records = glucose_result.scalars().all()

    glucose_summary = _compute_glucose_summary(glucose_records)

    # ── Complication status from alerts ───────────────────────────────────
    alert_stmt = (
        select(Alert)
        .where(Alert.patient_id == patient_id)
        .order_by(desc(Alert.created_at))
        .limit(50)
    )
    alert_result = await db.execute(alert_stmt)
    alerts = alert_result.scalars().all()

    complication_status = _summarize_complications(alerts)

    # ── Questions for receiving physician ─────────────────────────────────
    questions = [
        "是否需要调整当前降糖方案？",
        "是否需要进一步检查（如C肽、胰岛素抗体）？",
        "转诊目标科室是否合适？",
    ]

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "patient_demographics": demographics,
        "current_medications": current_medications,
        "medication_count": len(current_medications),
        "recent_lab_results": recent_labs,
        "hba1c_history": hba1c_history,
        "glucose_control_summary": glucose_summary,
        "complication_status": complication_status,
        "questions_for_receiving_physician": questions,
    }


def _compute_glucose_summary(records: list[GlucoseRecord]) -> dict[str, Any]:
    """Compute glucose TIR and trend from records."""
    if not records:
        return {
            "total_records": 0,
            "avg_mmol_l": None,
            "in_range_pct": None,
            "above_range_pct": None,
            "below_range_pct": None,
            "trend": "insufficient_data",
        }

    values = [r.value_mmol_l for r in records]
    avg = round(sum(values) / len(values), 1)
    max_val = max(values)
    min_val = min(values)

    in_range = sum(1 for v in values if 3.9 <= v <= 10.0)
    above_range = sum(1 for v in values if v > 10.0)
    below_range = sum(1 for v in values if v < 3.9)
    total = len(values)

    # Determine trend from the first half vs second half
    mid = total // 2
    trend = "stable"
    if mid > 0:
        first_half_avg = sum(values[:mid]) / mid
        second_half_avg = sum(values[mid:]) / (total - mid)
        if second_half_avg > first_half_avg * 1.1:
            trend = "worsening"
        elif second_half_avg < first_half_avg * 0.9:
            trend = "improving"

    return {
        "total_records": total,
        "avg_mmol_l": avg,
        "max_mmol_l": max_val,
        "min_mmol_l": min_val,
        "in_range_pct": round(in_range / total * 100, 1),
        "above_range_pct": round(above_range / total * 100, 1),
        "below_range_pct": round(below_range / total * 100, 1),
        "trend": trend,
    }


def _summarize_complications(alerts: list[Alert]) -> dict[str, Any]:
    """Extract complication status from alert history."""
    complication_keywords = {
        "肾病": "nephropathy",
        "视网膜": "retinopathy",
        "神经": "neuropathy",
        "足": "foot",
        "心血管": "cvd",
        "低血糖": "hypoglycemia",
        "酮症": "ketoacidosis",
    }

    status: dict[str, str] = {}
    for alert in alerts:
        for keyword, key in complication_keywords.items():
            if keyword in alert.title or keyword in alert.detail:
                if key not in status:
                    status[key] = alert.severity.value

    has_complications = len(status) > 0

    return {
        "has_known_complications": has_complications,
        "details": status,
        "recent_alert_count": len(alerts),
    }
