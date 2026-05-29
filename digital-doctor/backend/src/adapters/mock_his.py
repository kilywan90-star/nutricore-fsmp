"""Mock HIS Data Generator — realistic synthetic patient data for dev/demo.

No real hospital connection needed. Generates realistic distributions
matching T2DM epidemiology for the Chinese population.
"""

import hashlib
import random
import uuid
from datetime import date, datetime, timedelta


# Deterministic seed for reproducibility
_SEED = 42
_random = random.Random(_SEED)

# ── Chinese name generation ──────────────────────────────────────────────────
_SURNAMES = ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
             "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗", "梁"]

_MALE_GIVEN = ["伟", "强", "磊", "军", "勇", "涛", "明", "超", "华", "建国",
               "文博", "志远", "浩然", "子轩", "宇轩", "鹏飞", "俊杰", "泽宇"]

_FEMALE_GIVEN = ["芳", "敏", "静", "丽", "婷", "秀英", "雪梅", "晓红", "玉兰",
                 "婉婷", "诗涵", "梓涵", "雨涵", "梦瑶", "思琪", "欣怡", "雅文"]

# ── Treatment stages with T2DM-typical progression ───────────────────────────
TREATMENT_STAGES = [
    ("new_diagnosis", 0.20, "新诊断"),
    ("oral_medication", 0.40, "口服降糖药"),
    ("insulin", 0.25, "胰岛素治疗"),
    ("combination", 0.15, "联合治疗"),
]

# Oral medications
ORAL_MEDS = [
    ("二甲双胍", "500mg", "bid"),
    ("二甲双胍缓释片", "1000mg", "qd"),
    ("格列美脲", "2mg", "qd"),
    ("阿卡波糖", "50mg", "tid"),
    ("达格列净", "10mg", "qd"),
    ("西格列汀", "100mg", "qd"),
    ("吡格列酮", "15mg", "qd"),
    ("格列齐特", "80mg", "bid"),
]

# Insulin types
INSULIN_TYPES = [
    ("甘精胰岛素", "10U", "qd", ["20:00"]),
    ("地特胰岛素", "12U", "qd", ["21:00"]),
    ("门冬胰岛素", "6U", "tid", ["07:00", "12:00", "18:00"]),
    ("赖脯胰岛素", "5U", "tid", ["07:00", "12:00", "18:00"]),
    ("预混胰岛素30R", "16U", "bid", ["07:30", "17:30"]),
    ("德谷胰岛素", "8U", "qd", ["21:00"]),
]

# Common lab test panels
LAB_PANELS = [
    ("blood_glucose_panel", "血糖检测", ["fpg", "2hpg", "hba1c"]),
    ("full_metabolic_panel", "代谢全套", ["fpg", "hba1c", "tc", "ldl", "hdl", "tg"]),
    ("renal_function", "肾功能", ["creatinine", "bun", "egfr", "uacr"]),
    ("lipid_panel", "血脂四项", ["tc", "ldl", "hdl", "tg"]),
    ("hba1c_only", "糖化血红蛋白", ["hba1c"]),
]


def _deterministic_seed(patient_index: int) -> None:
    """Reset random state for deterministic generation per patient index."""
    _random.seed(_SEED + patient_index)


def _hash_patient_id(name: str, idx: int) -> str:
    """Generate a deterministic patient ID hash."""
    return hashlib.sha256(f"{name}:{idx}".encode()).hexdigest()[:32]


def _generate_name(male: bool) -> str:
    """Generate a realistic Chinese name."""
    surname = _random.choice(_SURNAMES)
    given_pool = _MALE_GIVEN if male else _FEMALE_GIVEN
    given = _random.choice(given_pool)
    # 30% chance of two-character given name
    if _random.random() < 0.3:
        given = _random.choice(given_pool)
    return surname + given


def _generate_age() -> int:
    """Generate age with T2DM epidemiology distribution (peak 45-65)."""
    # Rough triangular distribution
    r = _random.random()
    if r < 0.10:
        return _random.randint(18, 34)      # young onset
    elif r < 0.30:
        return _random.randint(35, 44)      # early middle age
    elif r < 0.70:
        return _random.randint(45, 60)      # peak
    elif r < 0.90:
        return _random.randint(61, 70)      # late middle age
    else:
        return _random.randint(71, 85)      # elderly


def _generate_glucose(controlled: bool) -> float:
    """Generate realistic glucose value."""
    if controlled:
        return round(_random.gauss(5.8, 0.8), 1)
    else:
        return round(_random.gauss(9.0, 2.5), 1)


def _generate_hba1c(controlled: bool) -> float:
    """Generate realistic HbA1c value."""
    if controlled:
        return round(_random.gauss(6.5, 0.5), 1)
    else:
        return round(_random.gauss(8.5, 1.5), 1)


def _pick_treatment_stage() -> tuple[str, str]:
    """Pick treatment stage according to distribution."""
    r = _random.random()
    cumulative = 0.0
    for stage, prob, label in TREATMENT_STAGES:
        cumulative += prob
        if r < cumulative:
            return stage, label
    return "oral_medication", "口服降糖药"


def generate_mock_patient_panel(count: int = 50) -> list[dict]:
    """Generate a panel of realistic mock T2DM patients.

    Distribution:
    - Age: peaks at 45-65 (matches T2DM epidemiology)
    - Gender: ~55% male
    - Treatment stages: new diagnosis 20%, oral 40%, insulin 25%, combination 15%
    - Glucose/HbA1c: realistic distributions (mix of controlled/uncontrolled)
    """
    patients: list[dict] = []
    current_year = date.today().year

    for i in range(count):
        _deterministic_seed(i)

        is_male = _random.random() < 0.55
        name = _generate_name(is_male)
        age = _generate_age()
        birth_year = current_year - age
        gender = "M" if is_male else "F"
        stage, stage_label = _pick_treatment_stage()

        # New diagnosis patients have shorter disease duration, otherwise 0-15 years
        if stage == "new_diagnosis":
            duration_years = _random.randint(0, 1)
        else:
            duration_years = _random.randint(1, 15)

        diagnosis_year = current_year - duration_years
        diagnosis_month = _random.randint(1, 12)
        diagnosis_day = _random.randint(1, 28)
        diagnosis_date = date(diagnosis_year, diagnosis_month, diagnosis_day)

        # Controlled probability depends on stage
        if stage == "new_diagnosis":
            controlled = _random.random() < 0.4
        elif stage == "oral_medication":
            controlled = _random.random() < 0.55
        elif stage == "insulin":
            controlled = _random.random() < 0.35
        else:
            controlled = _random.random() < 0.45

        patients.append({
            "fhir_id": f"mock-pat-{i:04d}",
            "name_hash": _hash_patient_id(name, i),
            "name_display": name,
            "gender": gender,
            "birth_year": birth_year,
            "age": age,
            "diabetes_type": "2型糖尿病",
            "diagnosis_date": diagnosis_date.isoformat(),
            "treatment_stage": stage,
            "treatment_stage_label": stage_label,
            "hba1c_target": 7.0,
            "controlled": controlled,
            "latest_glucose": _generate_glucose(controlled),
            "latest_hba1c": _generate_hba1c(controlled),
        })

    return patients


def generate_mock_glucose_history(patient_id: str, days: int = 90) -> list[dict]:
    """Generate realistic glucose records for a patient over N days.

    Includes daily patterns:
    - Fasting glucose in the morning (06:00-08:00)
    - Postprandial after meals (10:00, 14:00, 20:00)
    - Some missing days (real compliance is ~70%)
    - Day-to-day variability around a baseline
    """
    # Derive deterministic state from patient_id
    seed = sum(ord(c) for c in patient_id)
    _random.seed(_SEED + seed)

    records: list[dict] = []
    today = date.today()
    base_fpg = round(_random.gauss(7.0, 1.5), 1)

    for day_offset in range(days):
        record_date = today - timedelta(days=day_offset)

        # ~70% compliance — some days missing
        if _random.random() > 0.70 and day_offset > 0:
            continue

        # Fasting glucose (morning, varies around baseline)
        fpg_hour = _random.randint(6, 8)
        fpg_minute = _random.randint(0, 59)
        fpg_value = round(_random.gauss(base_fpg, 0.8), 1)
        fpg_value = max(2.5, min(20.0, fpg_value))

        records.append({
            "patient_id": patient_id,
            "value_mmol_l": fpg_value,
            "measure_type": "fasting",
            "recorded_at": datetime(
                record_date.year, record_date.month, record_date.day,
                fpg_hour, fpg_minute, _random.randint(0, 59),
            ).isoformat(),
            "notes": "",
        })

        # Post-breakfast (2h after)
        if _random.random() > 0.30:
            ppg_value = round(fpg_value * _random.uniform(1.3, 2.0), 1)
            ppg_value = max(3.0, min(22.0, ppg_value))
            records.append({
                "patient_id": patient_id,
                "value_mmol_l": ppg_value,
                "measure_type": "postprandial",
                "recorded_at": datetime(
                    record_date.year, record_date.month, record_date.day,
                    10, _random.randint(0, 59), _random.randint(0, 59),
                ).isoformat(),
                "notes": "早餐后2h",
            })

        # Post-lunch (2h after noon)
        if _random.random() > 0.40:
            lunch_value = round(_random.gauss(base_fpg * 1.4, 1.0), 1)
            lunch_value = max(3.0, min(22.0, lunch_value))
            records.append({
                "patient_id": patient_id,
                "value_mmol_l": lunch_value,
                "measure_type": "postprandial",
                "recorded_at": datetime(
                    record_date.year, record_date.month, record_date.day,
                    14, _random.randint(0, 59), _random.randint(0, 59),
                ).isoformat(),
                "notes": "午餐后2h",
            })

        # Evening
        if _random.random() > 0.50:
            evening_value = round(_random.gauss(base_fpg * 1.2, 1.0), 1)
            evening_value = max(2.5, min(20.0, evening_value))
            records.append({
                "patient_id": patient_id,
                "value_mmol_l": evening_value,
                "measure_type": "postprandial",
                "recorded_at": datetime(
                    record_date.year, record_date.month, record_date.day,
                    20, _random.randint(0, 59), _random.randint(0, 59),
                ).isoformat(),
                "notes": "晚餐后2h",
            })

    # Sort descending by date
    records.sort(key=lambda r: r["recorded_at"], reverse=True)
    return records


def generate_mock_lab_orders(patient_id: str) -> list[dict]:
    """Generate realistic lab orders matching T2DM guideline recommendations.

    Based on 中国2型糖尿病防治指南(2024版):
    - HbA1c every 3-6 months
    - Lipid panel every 6-12 months
    - Renal function every 6-12 months
    - Eye exam annually
    """
    seed = sum(ord(c) for c in patient_id)
    _random.seed(_SEED + seed)

    orders: list[dict] = []
    today = date.today()

    # HbA1c every 3 months (4 in past year)
    for i in range(4):
        order_date = today - timedelta(days=90 * i + _random.randint(-10, 10))
        orders.append({
            "patient_id": patient_id,
            "order_type": "hba1c_only",
            "order_name": "糖化血红蛋白",
            "order_date": max(order_date, date.today() - timedelta(days=365)).isoformat(),
            "status": "completed",
            "items": ["hba1c"],
        })

    # Lipid panel every 6 months
    for i in range(2):
        order_date = today - timedelta(days=180 * i + _random.randint(-15, 15))
        orders.append({
            "patient_id": patient_id,
            "order_type": "lipid_panel",
            "order_name": "血脂四项",
            "order_date": max(order_date, date.today() - timedelta(days=365)).isoformat(),
            "status": "completed",
            "items": ["tc", "ldl", "hdl", "tg"],
        })

    # Renal function every 6 months
    for i in range(2):
        order_date = today - timedelta(days=180 * i + _random.randint(-15, 15) + 30)
        orders.append({
            "patient_id": patient_id,
            "order_type": "renal_function",
            "order_name": "肾功能",
            "order_date": max(order_date, date.today() - timedelta(days=365)).isoformat(),
            "status": "completed",
            "items": ["creatinine", "bun", "egfr"],
        })

    # Annual comprehensive metabolic panel
    orders.append({
        "patient_id": patient_id,
        "order_type": "full_metabolic_panel",
        "order_name": "代谢全套",
        "order_date": (today - timedelta(days=_random.randint(30, 300))).isoformat(),
        "status": "completed",
        "items": ["fpg", "hba1c", "tc", "ldl", "hdl", "tg", "creatinine", "bun", "egfr"],
    })

    # Eye exam annually
    orders.append({
        "patient_id": patient_id,
        "order_type": "ophthalmology",
        "order_name": "眼底检查",
        "order_date": (today - timedelta(days=_random.randint(30, 365))).isoformat(),
        "status": "completed",
        "items": ["fundus_photo"],
    })

    orders.sort(key=lambda o: o["order_date"], reverse=True)
    return orders


def generate_mock_medications(patient_id: str) -> list[dict]:
    """Generate realistic medication list based on treatment stage."""
    seed = sum(ord(c) for c in patient_id)
    _random.seed(_SEED + seed)

    r = _random.random()
    if r < 0.20:  # new diagnosis
        return []

    today = date.today()
    meds: list[dict] = []

    if r < 0.60:  # oral only or oral + insulin
        oral = _random.choice(ORAL_MEDS)
        start = today - timedelta(days=_random.randint(30, 1095))
        meds.append({
            "patient_id": patient_id,
            "drug_name": oral[0],
            "dosage": oral[1],
            "frequency": oral[2],
            "time_of_day": ["07:00", "18:00"] if oral[2] == "bid" else
                            (["07:00", "12:00", "18:00"] if oral[2] == "tid" else ["07:30"]),
            "start_date": start.isoformat(),
            "end_date": None,
            "is_active": True,
        })

    if r >= 0.40:  # insulin or combination
        insulin = _random.choice(INSULIN_TYPES)
        insulin_start = today - timedelta(days=_random.randint(30, 730))
        meds.append({
            "patient_id": patient_id,
            "drug_name": insulin[0],
            "dosage": insulin[1],
            "frequency": insulin[2],
            "time_of_day": list(insulin[3]),
            "start_date": insulin_start.isoformat(),
            "end_date": None,
            "is_active": True,
        })

    return meds
