"""Database seed script — creates realistic demo data for development and testing.

Usage: python -m src.db.seed
"""

import asyncio
import hashlib
import random
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import async_session_factory
from src.models.patient import Patient, GlucoseRecord, MedicationReminder
from src.models.clinical import LabReport, Alert, AlertSeverity

_SEED = 42
_random = random.Random(_SEED)


# ── Demo patient templates ───────────────────────────────────────────────────
_DEMO_PATIENTS = [
    # (name_display, gender, birth_year, diabetes_type, diagnosis_offset_days, hba1c_target)
    ("李建国", "M", 1965, "2型糖尿病", 2920, 7.0),   # ~8 years ago
    ("王秀英", "F", 1958, "2型糖尿病", 3650, 7.5),   # ~10 years
    ("张伟强", "M", 1972, "2型糖尿病", 2190, 6.5),   # ~6 years
    ("刘芳梅", "F", 1968, "2型糖尿病", 5475, 7.0),   # ~15 years
    ("陈志远", "M", 1980, "2型糖尿病", 1095, 7.0),   # ~3 years
    ("杨雪梅", "F", 1963, "2型糖尿病", 6205, 8.0),   # ~17 years
    ("赵鹏飞", "M", 1955, "2型糖尿病", 7300, 8.0),   # ~20 years
    ("黄婉婷", "F", 1975, "2型糖尿病", 2555, 6.5),   # ~7 years
    ("周建国", "M", 1960, "2型糖尿病", 5100, 7.0),   # ~14 years
    ("吴雅文", "F", 1985, "2型糖尿病", 1460, 6.5),   # ~4 years
    ("孙磊", "M", 1970, "2型糖尿病", 2555, 7.0),
    ("胡敏", "F", 1962, "2型糖尿病", 7300, 7.5),
    ("朱军", "M", 1978, "2型糖尿病", 1825, 7.0),
    ("高静", "F", 1959, "2型糖尿病", 8760, 8.0),
    ("林涛", "M", 1967, "2型糖尿病", 3650, 7.0),
    ("何丽", "F", 1982, "2型糖尿病", 730, 6.5),     # ~2 years
    ("郭明", "M", 1974, "2型糖尿病", 2190, 7.0),
    ("马玉兰", "F", 1966, "2型糖尿病", 4380, 7.0),
    ("罗超", "M", 1988, "2型糖尿病", 365, 6.5),      # ~1 year
    ("梁晓红", "F", 1971, "2型糖尿病", 1825, 7.0),
]

# ── Medications ──────────────────────────────────────────────────────────────
_ORAL_MEDS = [
    ("二甲双胍", "500mg", "bid", ["07:00", "18:00"]),
    ("二甲双胍缓释片", "1000mg", "qd", ["07:30"]),
    ("格列美脲", "2mg", "qd", ["07:00"]),
    ("阿卡波糖", "50mg", "tid", ["07:00", "12:00", "18:00"]),
    ("达格列净", "10mg", "qd", ["07:30"]),
    ("西格列汀", "100mg", "qd", ["07:00"]),
    ("吡格列酮", "15mg", "qd", ["07:30"]),
    ("格列齐特", "80mg", "bid", ["07:00", "18:00"]),
]

_INSULIN_MEDS = [
    ("甘精胰岛素", "10U", "qd", ["20:00"]),
    ("门冬胰岛素", "6U", "tid", ["07:00", "12:00", "18:00"]),
    ("预混胰岛素30R", "16U", "bid", ["07:30", "17:30"]),
    ("德谷胰岛素", "8U", "qd", ["21:00"]),
]

# ── Alert templates ──────────────────────────────────────────────────────────
_ALERT_TEMPLATES = [
    {
        "alert_type": "severe_hyperglycemia",
        "severity": AlertSeverity.CRITICAL,
        "title": "严重高血糖预警",
        "detail": "近期血糖持续偏高，空腹血糖>=11.1mmol/L，需立即调整治疗方案",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 12.1节",
    },
    {
        "alert_type": "consecutive_high_fpg",
        "severity": AlertSeverity.WARNING,
        "title": "空腹血糖持续偏高",
        "detail": "连续3天空腹血糖>=7.0mmol/L，建议复查并调整用药",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 8.2节",
    },
    {
        "alert_type": "hba1c_above_target",
        "severity": AlertSeverity.WARNING,
        "title": "糖化血红蛋白未达标",
        "detail": "最新HbA1c高于个体化控制目标，建议加强血糖管理",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 8.3节",
    },
    {
        "alert_type": "hypoglycemia",
        "severity": AlertSeverity.WARNING,
        "title": "低血糖风险预警",
        "detail": "近期出现低血糖事件，请调整降糖药物剂量",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 12.2节",
    },
    {
        "alert_type": "renal_function_decline",
        "severity": AlertSeverity.WARNING,
        "title": "肾功能下降预警",
        "detail": "eGFR持续下降，请关注肾功能变化并考虑药物剂量调整",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 13.1节",
    },
    {
        "alert_type": "lipid_abnormality",
        "severity": AlertSeverity.WARNING,
        "title": "血脂异常提醒",
        "detail": "血脂检测结果异常，建议启动或调整降脂治疗",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 9.1节",
    },
    {
        "alert_type": "missed_followup",
        "severity": AlertSeverity.INFO,
        "title": "随访到期提醒",
        "detail": "患者已超过3个月未进行糖化血红蛋白检测",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 10.2节",
    },
    {
        "alert_type": "eye_exam_reminder",
        "severity": AlertSeverity.INFO,
        "title": "年度眼底检查提醒",
        "detail": "请安排年度糖尿病视网膜病变筛查",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 13.3节",
    },
    {
        "alert_type": "medication_adherence",
        "severity": AlertSeverity.INFO,
        "title": "用药依从性提醒",
        "detail": "近期用药记录不规律，请提醒患者按时服药",
        "reference_guideline": "中国2型糖尿病防治指南(2024版) 7.1节",
    },
    {
        "alert_type": "new_guideline_update",
        "severity": AlertSeverity.INFO,
        "title": "指南更新通知",
        "detail": "中国2型糖尿病防治指南已更新，请关注最新诊疗建议",
        "reference_guideline": "中国2型糖尿病防治指南(2024版)",
    },
]


def _hash_name(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:32]


def _deterministic_seed(idx: int) -> None:
    _random.seed(_SEED + idx)


async def seed_demo_data(db: AsyncSession, patient_count: int = 20) -> int:
    """Create demo patients with glucose records, lab reports, medications, and alerts.

    Returns the number of patients created.
    """
    today = date.today()
    patients_to_create = min(patient_count, len(_DEMO_PATIENTS))

    for i in range(patients_to_create):
        _deterministic_seed(i)

        name, gender, birth_year, diabetes_type, diag_offset_days, hba1c_target = _DEMO_PATIENTS[i]
        diagnosis_date = today - timedelta(days=diag_offset_days)
        patient_id = uuid.uuid4()

        # ── Create Patient ───────────────────────────────────────────────────
        patient = Patient(
            id=patient_id,
            name_hash=_hash_name(name),
            gender=gender,
            birth_year=birth_year,
            diabetes_type=diabetes_type,
            diagnosis_date=diagnosis_date,
            hba1c_target=hba1c_target,
        )
        db.add(patient)

        # ── Glucose records (2-3 months, ~90 days) ───────────────────────────
        base_fpg = round(_random.gauss(7.0, 1.5), 1)
        for day_offset in range(90):
            record_date = today - timedelta(days=day_offset)

            # ~70% compliance
            if _random.random() > 0.70 and day_offset > 0:
                continue

            # Fasting glucose
            fpg_value = round(_random.gauss(base_fpg, 0.8), 1)
            fpg_value = max(2.5, min(20.0, fpg_value))
            fpg_hour = _random.randint(6, 8)
            db.add(GlucoseRecord(
                patient_id=patient_id,
                value_mmol_l=fpg_value,
                measure_type="fasting",
                recorded_at=datetime(record_date.year, record_date.month, record_date.day,
                                     fpg_hour, _random.randint(0, 59), _random.randint(0, 59)),
            ))

            # Postprandial occasionally
            if _random.random() > 0.30:
                ppg_value = round(fpg_value * _random.uniform(1.3, 2.0), 1)
                ppg_value = max(3.0, min(22.0, ppg_value))
                db.add(GlucoseRecord(
                    patient_id=patient_id,
                    value_mmol_l=ppg_value,
                    measure_type="postprandial",
                    recorded_at=datetime(record_date.year, record_date.month, record_date.day,
                                         10, _random.randint(0, 59), _random.randint(0, 59)),
                    notes="早餐后2h",
                ))

        # ── Lab reports (1-2 per patient) ────────────────────────────────────
        num_reports = _random.randint(1, 2)
        for r_idx in range(num_reports):
            report_date = today - timedelta(days=_random.randint(7, 180))
            if r_idx == 0:
                results = {
                    "fpg": round(_random.gauss(7.0, 1.5), 1),
                    "hba1c": round(_random.gauss(7.2, 1.2), 1),
                    "tc": round(_random.gauss(5.5, 1.0), 1),
                    "ldl": round(_random.gauss(3.5, 1.0), 1),
                    "hdl": round(_random.gauss(1.1, 0.3), 1),
                    "tg": round(_random.gauss(2.0, 1.0), 1),
                }
                report_type = "full_metabolic_panel"
            else:
                results = {
                    "hba1c": round(_random.gauss(7.2, 1.2), 1),
                }
                report_type = "hba1c_only"

            db.add(LabReport(
                patient_id=patient_id,
                report_type=report_type,
                report_date=report_date,
                results=results,
                ai_interpretation="基于检测结果，建议维持当前治疗方案并加强生活方式干预",
            ))

        # ── Medication reminders ─────────────────────────────────────────────
        stage_roll = _random.random()
        if stage_roll >= 0.20:  # 80% have medication (not new diagnosis)
            oral = _random.choice(_ORAL_MEDS)
            oral_start = today - timedelta(days=_random.randint(30, 1095))
            db.add(MedicationReminder(
                patient_id=patient_id,
                drug_name=oral[0],
                dosage=oral[1],
                frequency=oral[2],
                time_of_day=list(oral[3]),
                start_date=oral_start,
                end_date=None,
                is_active=True,
            ))

            if stage_roll >= 0.55:  # insulin or combination
                insulin = _random.choice(_INSULIN_MEDS)
                insulin_start = today - timedelta(days=_random.randint(30, 730))
                db.add(MedicationReminder(
                    patient_id=patient_id,
                    drug_name=insulin[0],
                    dosage=insulin[1],
                    frequency=insulin[2],
                    time_of_day=list(insulin[3]),
                    start_date=insulin_start,
                    end_date=None,
                    is_active=True,
                ))

        # ── Alerts (5-10 per patient, mix of acknowledged/unacknowledged) ────
        num_alerts = _random.randint(5, 10)
        selected_alerts = _random.sample(_ALERT_TEMPLATES, min(num_alerts, len(_ALERT_TEMPLATES)))

        # Ensure at least 2 unacknowledged
        unacknowledged_count = max(2, num_alerts - _random.randint(0, 3))

        for a_idx, template in enumerate(selected_alerts):
            days_ago = _random.randint(0, 30)
            acknowledged = a_idx >= unacknowledged_count
            db.add(Alert(
                patient_id=patient_id,
                alert_type=template["alert_type"],
                severity=template["severity"],
                title=template["title"],
                detail=template["detail"],
                reference_guideline=template["reference_guideline"],
                acknowledged=acknowledged,
                created_at=datetime.utcnow() - timedelta(days=days_ago),
            ))

    await db.commit()
    return patients_to_create


async def _main():
    """Seed demo data and print summary."""
    async with async_session_factory() as session:
        count = await seed_demo_data(session, patient_count=20)
        print(f"Seeded {count} patients with demo data.")
        print("  - 2-3 months of glucose records per patient")
        print("  - 1-2 lab reports per patient")
        print("  - Medication reminders (80% with meds)")
        print("  - 5-10 alerts per patient (mix of acknowledged/unacknowledged)")


if __name__ == "__main__":
    asyncio.run(_main())
