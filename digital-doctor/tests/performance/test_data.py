"""
Realistic test data pool for Locust load tests.

Generates deterministic user credentials, patient profiles, and doctor profiles
that can be seeded into the database before running load tests.
"""

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Seed data pools
# ---------------------------------------------------------------------------

PATIENT_GENDERS = ["M", "F"]
PATIENT_BIRTH_YEARS = list(range(1940, 2006))
PATIENT_DIABETES_TYPES = ["type1", "type2", "prediabetes", "gestational"]

DOCTOR_TITLES = ["主治医师", "副主任医师", "主任医师", "住院医师"]
DOCTOR_DEPARTMENTS = [
    ("内分泌科", "endocrinology"),
    ("心内科", "cardiology"),
    ("全科", "general"),
    ("肾内科", "nephrology"),
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TestPatient:
    index: int
    phone_hash: str
    password: str
    name_hash: str
    gender: str
    birth_year: int
    diabetes_type: str
    access_token: Optional[str] = None


@dataclass
class TestDoctor:
    index: int
    phone_hash: str
    password: str
    title: str
    department_code: str
    department_name: str
    access_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Deterministic generation helpers
# ---------------------------------------------------------------------------


def _make_hash(prefix: str, idx: int) -> str:
    raw = f"{prefix}_{idx:04d}_digital_doctor"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Generated pools
# ---------------------------------------------------------------------------


def generate_patients(count: int = 50) -> list[TestPatient]:
    pool = []
    for i in range(count):
        pool.append(
            TestPatient(
                index=i,
                phone_hash=_make_hash("patient_phone", i),
                password=f"test_pwd_{i:04d}",
                name_hash=_make_hash("patient_name", i),
                gender=random.choice(PATIENT_GENDERS),
                birth_year=random.choice(PATIENT_BIRTH_YEARS),
                diabetes_type=random.choice(PATIENT_DIABETES_TYPES),
            )
        )
    return pool


def generate_doctors(count: int = 10) -> list[TestDoctor]:
    pool = []
    for i in range(count):
        dept_name, dept_code = DOCTOR_DEPARTMENTS[i % len(DOCTOR_DEPARTMENTS)]
        pool.append(
            TestDoctor(
                index=i,
                phone_hash=_make_hash("doctor_phone", i),
                password=f"doc_pwd_{i:04d}",
                title=DOCTOR_TITLES[i % len(DOCTOR_TITLES)],
                department_code=dept_code,
                department_name=dept_name,
            )
        )
    return pool


# ---------------------------------------------------------------------------
# Singleton pools
# ---------------------------------------------------------------------------

PATIENTS = generate_patients(50)
DOCTORS = generate_doctors(10)


def get_patient(idx: int) -> TestPatient:
    return PATIENTS[idx % len(PATIENTS)]


def get_doctor(idx: int) -> TestDoctor:
    return DOCTORS[idx % len(DOCTORS)]


# ---------------------------------------------------------------------------
# Glucose measurement types for test data
# ---------------------------------------------------------------------------

GLUCOSE_MEASURE_TYPES = ["fasting", "pre_meal", "post_prandial", "bedtime", "random"]

BLOOD_SUGAR_RANGES = {
    "fasting": (3.5, 7.0),
    "pre_meal": (3.5, 7.5),
    "post_prandial": (4.0, 11.0),
    "bedtime": (4.0, 9.0),
    "random": (3.5, 11.0),
}


def random_glucose(measure_type: str = "fasting") -> float:
    lo, hi = BLOOD_SUGAR_RANGES.get(measure_type, (3.5, 11.0))
    return round(random.uniform(lo, hi), 1)


# ---------------------------------------------------------------------------
# Health coach test messages
# ---------------------------------------------------------------------------

COACH_MESSAGES = [
    "我今天空腹血糖6.8，比平时高一点，需要注意什么？",
    "最近总是觉得口渴，是不是血糖控制不好了？",
    "我今天晚餐后两小时血糖9.5，正常吗？",
    "运动后血糖反而升高了，这是为什么？",
    "我该在什么时间测血糖最准确？",
    "最近经常出现低血糖，应该怎么调整饮食？",
    "我今天感觉头晕乏力，是不是药物副作用？",
    "请问二甲双胍应该饭前还是饭后服用？",
]


def random_coach_message() -> str:
    return random.choice(COACH_MESSAGES)


# ---------------------------------------------------------------------------
# Risk assessment test data
# ---------------------------------------------------------------------------


def random_risk_assessment() -> dict:
    return {
        "age": random.randint(25, 75),
        "bmi": round(random.uniform(18.5, 35.0), 1),
        "waist_circumference": round(random.uniform(60, 120), 1),
        "family_history": random.choice([True, False]),
        "physical_activity": random.choice(["high", "moderate", "low"]),
        "fasting_glucose": round(random.uniform(3.5, 12.0), 1),
        "has_hypertension": random.choice([True, False]),
    }
