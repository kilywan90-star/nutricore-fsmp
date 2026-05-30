"""
Locust load test suite for digital-doctor.

Simulates realistic user workflows:
  - PatientUser: login -> risk assessment -> glucose stats -> health coach -> notifications
  - DoctorUser:  login -> patient list -> patient detail -> patient alerts
  - MixedUser:   80% patient + 20% doctor concurrency mix

Usage:
    locust -f digital-doctor/tests/performance/locustfile.py --host=http://localhost:8000

Environment variables:
    LOCUST_HOST        — override host (same as --host flag)
    PERFORMANCE_SEED   — seed data index offset (default 0)
    PRE_REGISTERED     — set "true" if users already exist in DB (skips register)
"""

import os
import random
import hashlib
from locust import HttpUser, task, between, TaskSet

from tests.performance.test_data import (
    get_patient,
    get_doctor,
    random_glucose,
    random_coach_message,
    random_risk_assessment,
    PATIENTS,
    DOCTORS,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HOST = os.environ.get("LOCUST_HOST", "http://localhost:8000")
SEED_OFFSET = int(os.environ.get("PERFORMANCE_SEED", "0"))
PRE_REGISTERED = os.environ.get("PRE_REGISTERED", "").lower() == "true"


def _phash(prefix: str, idx: int) -> str:
    return hashlib.sha256(f"{prefix}_{idx:04d}_digital_doctor".encode()).hexdigest()


# ---------------------------------------------------------------------------
# Auth helper — called once per user during on_start
# ---------------------------------------------------------------------------


def authenticate(client, phone_hash: str, password: str, role: str) -> str:
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"phone_hash": phone_hash, "password": password},
        name="/auth/login",
    )
    if login_resp.status_code == 200:
        return login_resp.json()["access_token"]

    # Register if not found
    if not PRE_REGISTERED and login_resp.status_code == 401:
        register_payload = {
            "phone_hash": phone_hash,
            "password": password,
            "name_hash": phone_hash,
            "gender": random.choice(["M", "F"]),
            "birth_year": random.randint(1940, 2000),
            "diabetes_type": random.choice(["type1", "type2", "prediabetes", "gestational"]),
        }
        reg_resp = client.post(
            "/api/v1/auth/register",
            json=register_payload,
            name="/auth/register",
        )
        if reg_resp.status_code == 200:
            login_resp2 = client.post(
                "/api/v1/auth/login",
                json={"phone_hash": phone_hash, "password": password},
                name="/auth/login",
            )
            if login_resp2.status_code == 200:
                return login_resp2.json()["access_token"]

    login_resp.failure("Auth failed — neither login nor register succeeded")
    return ""


# ---------------------------------------------------------------------------
# Patient workflow
# ---------------------------------------------------------------------------


class PatientUser(HttpUser):
    """Simulates a patient: login -> risk assessment -> glucose log -> health coach -> notifications."""

    wait_time = between(1, 3)
    _token: str = ""

    def on_start(self):
        idx = SEED_OFFSET + int(self.environment.runner.user_count) if self.environment.runner else 0
        p = get_patient(self._get_index())
        self._token = authenticate(self.client, p.phone_hash, p.password, "patient")
        if self._token:
            self.client.headers.update({"Authorization": f"Bearer {self._token}"})

    def _get_index(self) -> int:
        # Use a stable index derived from the user instance
        return id(self) % len(PATIENTS)

    @task(3)
    def risk_assessment(self):
        if not self._token:
            return
        payload = random_risk_assessment()
        with self.client.post(
            "/api/v1/patient/risk-assessment",
            json=payload,
            name="/patient/risk-assessment",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Risk assessment failed: {r.status_code}")

    @task(2)
    def glucose_stats(self):
        if not self._token:
            return
        values = [random_glucose(random.choice(["fasting", "pre_meal", "post_prandial"])) for _ in range(7)]
        with self.client.post(
            "/api/v1/patient/glucose-stats",
            json=values,
            name="/patient/glucose-stats",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Glucose stats failed: {r.status_code}")

    @task(1)
    def health_coach(self):
        if not self._token:
            return
        payload = {
            "message": random_coach_message(),
            "recent_fpg": [round(random.uniform(3.5, 8.0), 1) for _ in range(3)],
            "recent_ppg": [round(random.uniform(4.0, 11.0), 1) for _ in range(3)],
            "hba1c": round(random.uniform(5.5, 9.0), 1),
            "medications": random.choice([["二甲双胍"], ["二甲双胍", "胰岛素"], ["格列美脲"], []]),
            "diet_adherence": random.choice(["良好", "一般", "较差", "未知"]),
            "exercise_adherence": random.choice(["良好", "一般", "较差", "未知"]),
        }
        with self.client.post(
            "/api/v1/patient/health-coach",
            json=payload,
            name="/patient/health-coach",
            catch_response=True,
            timeout=10,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Health coach failed: {r.status_code}")

    @task(2)
    def notifications(self):
        if not self._token:
            return
        with self.client.get(
            "/api/v1/notifications",
            name="/notifications",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Notifications failed: {r.status_code}")


# ---------------------------------------------------------------------------
# Doctor workflow
# ---------------------------------------------------------------------------


class DoctorUser(HttpUser):
    """Simulates a doctor: login -> patient list -> patient detail -> alerts."""

    wait_time = between(1, 3)
    _token: str = ""

    def on_start(self):
        idx = SEED_OFFSET + int(self.environment.runner.user_count) if self.environment.runner else 0
        d = get_doctor(self._get_index())
        self._token = authenticate(self.client, d.phone_hash, d.password, "doctor")
        if self._token:
            self.client.headers.update({"Authorization": f"Bearer {self._token}"})

    def _get_index(self) -> int:
        return id(self) % len(DOCTORS)

    @task(3)
    def patient_list(self):
        if not self._token:
            return
        with self.client.get(
            "/api/v1/doctor/patients",
            params={"page": 1, "page_size": 20},
            name="/doctor/patients",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"Patient list failed: {r.status_code}")

    @task(2)
    def patient_detail(self):
        if not self._token:
            return
        # Use a known patient UUID from the seed; for real runs use actual IDs
        patient_id = "00000000-0000-0000-0000-000000000001"
        with self.client.get(
            f"/api/v1/doctor/patients/{patient_id}",
            name="/doctor/patients/{id}",
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 404):
                r.failure(f"Patient detail failed: {r.status_code}")

    @task(1)
    def patient_alerts(self):
        if not self._token:
            return
        patient_id = "00000000-0000-0000-0000-000000000001"
        with self.client.get(
            f"/api/v1/doctor/patients/{patient_id}/alerts",
            name="/doctor/patients/{id}/alerts",
            catch_response=True,
        ) as r:
            if r.status_code not in (200, 404):
                r.failure(f"Patient alerts failed: {r.status_code}")


# ---------------------------------------------------------------------------
# Mixed concurrency — 80% patient, 20% doctor
# ---------------------------------------------------------------------------


class MixedUser(HttpUser):
    """Mixed workload: 80% patient tasks, 20% doctor tasks."""

    wait_time = between(1, 3)
    _token: str = ""
    _role: str = ""

    def on_start(self):
        is_patient = random.random() < 0.8
        self._role = "patient" if is_patient else "doctor"
        idx = self._get_index()
        if is_patient:
            p = get_patient(idx)
            self._token = authenticate(self.client, p.phone_hash, p.password, "patient")
        else:
            d = get_doctor(idx)
            self._token = authenticate(self.client, d.phone_hash, d.password, "doctor")
        if self._token:
            self.client.headers.update({"Authorization": f"Bearer {self._token}"})

    def _get_index(self) -> int:
        return id(self) % max(len(PATIENTS), len(DOCTORS))

    @task(24)
    def patient_risk(self):
        """Patient risk assessment (24% weight = ~80% of 30 total)."""
        if not self._token or self._role != "patient":
            return
        self.client.post(
            "/api/v1/patient/risk-assessment",
            json=random_risk_assessment(),
            name="/patient/risk-assessment",
        )

    @task(16)
    def patient_glucose(self):
        """Patient glucose stats (16% weight)."""
        if not self._token or self._role != "patient":
            return
        values = [random_glucose() for _ in range(7)]
        self.client.post(
            "/api/v1/patient/glucose-stats",
            json=values,
            name="/patient/glucose-stats",
        )

    @task(8)
    def patient_coach(self):
        """Patient health coach (8% weight)."""
        if not self._token or self._role != "patient":
            return
        self.client.post(
            "/api/v1/patient/health-coach",
            json={"message": random_coach_message()},
            name="/patient/health-coach",
        )

    @task(16)
    def patient_notifications(self):
        """Patient notifications (16% weight)."""
        if not self._token or self._role != "patient":
            return
        self.client.get("/api/v1/notifications", name="/notifications")

    @task(18)
    def doctor_patient_list(self):
        """Doctor patient list (18% weight = ~60% of doctor share)."""
        if not self._token or self._role != "doctor":
            return
        self.client.get(
            "/api/v1/doctor/patients",
            params={"page": 1, "page_size": 20},
            name="/doctor/patients",
        )

    @task(12)
    def doctor_patient_detail(self):
        """Doctor patient detail (12% weight)."""
        if not self._token or self._role != "doctor":
            return
        self.client.get(
            "/api/v1/doctor/patients/00000000-0000-0000-0000-000000000001",
            name="/doctor/patients/{id}",
        )

    @task(6)
    def doctor_alerts(self):
        """Doctor patient alerts (6% weight)."""
        if not self._token or self._role != "doctor":
            return
        self.client.get(
            "/api/v1/doctor/patients/00000000-0000-0000-0000-000000000001/alerts",
            name="/doctor/patients/{id}/alerts",
        )

    # Total weight = 24+16+8+16+18+12+6 = 100
    # Patient share = 24+16+8+16 = 64 (64% of CPU time, but 80% of users)
    # Doctor share = 18+12+6 = 36
