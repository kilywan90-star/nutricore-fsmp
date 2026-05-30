"""Tests for critical alert closed-loop system — 3-tier escalation."""
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from src.config import settings
from src.models.user import User, UserRole
from src.models.patient import Patient
from src.models.org import DoctorProfile, PatientAssignment, Department, AssignmentType
from src.models.critical_alert import CriticalAlert, CriticalAlertStatus
from src.services.critical_alert_service import CriticalAlertService


_fixture_counter = 0


def _unique_phone() -> str:
    global _fixture_counter
    _fixture_counter += 1
    return f"test_phone_{_fixture_counter}"


@pytest.fixture
def patched_lightweight_mode(monkeypatch):
    """Set CLOSED_LOOP_MODE to lightweight for a test."""
    monkeypatch.setattr(settings, "CLOSED_LOOP_MODE", "lightweight")
    monkeypatch.setattr(settings, "CRITICAL_ALERT_ENABLED", True)


@pytest.fixture
def patched_standard_mode(monkeypatch):
    """Set CLOSED_LOOP_MODE to standard for a test."""
    monkeypatch.setattr(settings, "CLOSED_LOOP_MODE", "standard")
    monkeypatch.setattr(settings, "CRITICAL_ALERT_ENABLED", True)


@pytest.fixture
def patched_complete_mode(monkeypatch):
    """Set CLOSED_LOOP_MODE to complete for a test."""
    monkeypatch.setattr(settings, "CLOSED_LOOP_MODE", "complete")
    monkeypatch.setattr(settings, "CRITICAL_ALERT_ENABLED", True)


@pytest.fixture
async def doctor_user(db_session):
    """Create a doctor user with profile and department."""
    dept = Department(name="内分泌科", code="endo", is_active=True)
    db_session.add(dept)
    await db_session.flush()

    user = User(
        phone_hash=_unique_phone(),
        password_hash="hash",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    profile = DoctorProfile(
        user_id=user.id,
        department_id=dept.id,
        title="主治医师",
        is_active=True,
        is_department_head=False,
    )
    db_session.add(profile)
    await db_session.commit()
    return user.id


@pytest.fixture
async def dept_head_user(db_session):
    """Create a department head user."""
    dept = Department(name="急诊科", code="er_critical", is_active=True)
    db_session.add(dept)
    await db_session.flush()

    user = User(
        phone_hash=_unique_phone(),
        password_hash="hash",
        role=UserRole.DEPARTMENT_HEAD,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    profile = DoctorProfile(
        user_id=user.id,
        department_id=dept.id,
        title="主任医师",
        is_active=True,
        is_department_head=True,
    )
    db_session.add(profile)
    await db_session.commit()
    return user.id


@pytest.fixture
async def patient_with_doctor(db_session, doctor_user):
    """Create a patient assigned to the doctor."""
    patient = Patient(
        user_id=uuid.uuid4(),
        name_hash="critical_test_patient",
        gender="M",
        birth_year=1965,
        diabetes_type="type2",
    )
    db_session.add(patient)
    await db_session.flush()

    doctor_profile_stmt = select(DoctorProfile).where(DoctorProfile.user_id == doctor_user)
    result = await db_session.execute(doctor_profile_stmt)
    doctor_profile = result.scalar_one()

    assignment = PatientAssignment(
        patient_id=patient.id,
        doctor_id=doctor_profile.id,
        assignment_type=AssignmentType.PRIMARY,
        is_active=True,
    )
    db_session.add(assignment)
    await db_session.commit()
    return patient.id


# ── Test 1: trigger creates alert with DETECTED status ──────────────────

@pytest.mark.asyncio
async def test_trigger_creates_alert_with_detected_status(
    db_session, patient_with_doctor, patched_lightweight_mode,
):
    """Triggering a critical alert should create it with DETECTED status."""
    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=18.5,
        db=db_session,
    )
    assert alert is not None
    # In lightweight mode, _notify_doctor runs immediately, transitioning to NOTIFIED_DOCTOR
    assert alert.status == CriticalAlertStatus.NOTIFIED_DOCTOR
    assert alert.patient_id == patient_with_doctor
    assert alert.value == 18.5
    assert alert.alert_type == "severe_hyperglycemia"
    assert alert.severity == "critical"
    assert alert.status_history is not None
    assert len(alert.status_history) >= 2
    assert alert.status_history[0]["status"] == "detected"
    assert alert.status_history[1]["status"] == "notified_doctor"


# ── Test 2: lightweight mode: doctor acknowledge -> resolved ────────────

@pytest.mark.asyncio
async def test_lightweight_mode_doctor_acknowledge_resolves(
    db_session, patient_with_doctor, doctor_user, patched_lightweight_mode,
):
    """In lightweight mode, doctor acknowledging '已处理' resolves the alert."""
    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=20.0,
        db=db_session,
    )
    assert alert.status == CriticalAlertStatus.NOTIFIED_DOCTOR

    result = await CriticalAlertService.doctor_acknowledge(
        alert_id=alert.id,
        doctor_id=doctor_user,
        resolution="已处理",
        db=db_session,
    )
    assert result is not None
    assert result.status == CriticalAlertStatus.RESOLVED
    assert result.resolution == "已处理"
    assert result.acknowledged_by == doctor_user
    assert result.acknowledged_at is not None
    assert result.closed_at is not None


# ── Test 3: standard mode: doctor acknowledge -> nurse confirm -> resolved

@pytest.mark.asyncio
async def test_standard_mode_dual_confirm_flow(
    db_session, patient_with_doctor, doctor_user, patched_standard_mode,
):
    """In standard mode, doctor acknowledge + nurse confirm before resolved when '已联系患者'."""
    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="hypoglycemia",
        value=2.8,
        db=db_session,
    )

    # Doctor acknowledges with '已联系患者' - should NOT resolve in standard mode
    result = await CriticalAlertService.doctor_acknowledge(
        alert_id=alert.id,
        doctor_id=doctor_user,
        resolution="已联系患者",
        db=db_session,
    )
    assert result.status == CriticalAlertStatus.DOCTOR_ACKNOWLEDGED
    assert result.resolution == "已联系患者"

    # Nurse confirms - should resolve
    result2 = await CriticalAlertService.nurse_confirm(
        alert_id=result.id,
        nurse_id=doctor_user,  # same user, role doesn't matter for confirmation logic
        db=db_session,
    )
    assert result2.status == CriticalAlertStatus.RESOLVED
    assert result2.closed_at is not None


# ── Test 4: complete mode: doctor -> nurse -> patient notify -> resolved

@pytest.mark.asyncio
async def test_complete_mode_full_flow(
    db_session, patient_with_doctor, doctor_user, patched_complete_mode,
):
    """In complete mode, doctor acknowledge -> nurse confirm -> patient notified -> resolved."""
    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=22.0,
        db=db_session,
    )

    # Doctor acknowledges with '已联系患者'
    result = await CriticalAlertService.doctor_acknowledge(
        alert_id=alert.id,
        doctor_id=doctor_user,
        resolution="已联系患者",
        db=db_session,
    )
    assert result.status == CriticalAlertStatus.DOCTOR_ACKNOWLEDGED

    # Nurse confirms - should also notify patient and then resolve
    result2 = await CriticalAlertService.nurse_confirm(
        alert_id=result.id,
        nurse_id=doctor_user,
        db=db_session,
    )
    assert result2.status == CriticalAlertStatus.RESOLVED
    assert result2.closed_at is not None


# ── Test 5: timeout escalation ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_timeout_escalation(
    db_session, patient_with_doctor, patched_lightweight_mode, monkeypatch,
):
    """Alerts older than ACK_TIMEOUT should be escalated to department head."""
    monkeypatch.setattr(settings, "LIGHTWEIGHT_ACK_TIMEOUT_MINUTES", 1)

    # Create an alert
    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=18.0,
        db=db_session,
    )

    # Manually set detected_at to 2 minutes ago
    alert.detected_at = datetime.utcnow() - timedelta(minutes=2)
    await db_session.commit()

    # Run timeout check
    result = await CriticalAlertService.check_timeouts(db_session)
    assert result["escalated"] >= 1

    # Verify alert is now escalated
    await db_session.refresh(alert)
    assert alert.status == CriticalAlertStatus.ESCALATED


# ── Test 6: mode switching via config ───────────────────────────────────

@pytest.mark.asyncio
async def test_mode_switching_via_config(
    db_session, patient_with_doctor, doctor_user, monkeypatch,
):
    """Behavior should change when CLOSED_LOOP_MODE changes between lightweight/standard/complete."""
    # Start in lightweight mode
    monkeypatch.setattr(settings, "CLOSED_LOOP_MODE", "lightweight")
    monkeypatch.setattr(settings, "CRITICAL_ALERT_ENABLED", True)

    alert1 = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=17.0,
        db=db_session,
    )
    result1 = await CriticalAlertService.doctor_acknowledge(
        alert_id=alert1.id, doctor_id=doctor_user, resolution="已联系患者", db=db_session,
    )
    # In lightweight mode, '已联系患者' resolves immediately
    assert result1.status == CriticalAlertStatus.RESOLVED

    # Switch to standard mode
    monkeypatch.setattr(settings, "CLOSED_LOOP_MODE", "standard")

    alert2 = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=19.0,
        db=db_session,
    )
    result2 = await CriticalAlertService.doctor_acknowledge(
        alert_id=alert2.id, doctor_id=doctor_user, resolution="已联系患者", db=db_session,
    )
    # In standard mode, '已联系患者' stays as DOCTOR_ACKNOWLEDGED (waits for nurse)
    assert result2.status == CriticalAlertStatus.DOCTOR_ACKNOWLEDGED
    assert result2.resolution == "已联系患者"


# ── Test 7: status history tracking ─────────────────────────────────────

@pytest.mark.asyncio
async def test_status_history_tracking(
    db_session, patient_with_doctor, doctor_user, patched_lightweight_mode,
):
    """Status history should capture every transition with timestamp and user."""
    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=18.2,
        db=db_session,
    )

    result = await CriticalAlertService.doctor_acknowledge(
        alert_id=alert.id,
        doctor_id=doctor_user,
        resolution="已处理",
        db=db_session,
    )

    assert result.status_history is not None
    statuses = [h["status"] for h in result.status_history]
    assert "detected" in statuses
    assert "notified_doctor" in statuses
    assert "doctor_acknowledged" in statuses
    assert "resolved" in statuses

    # Verify timestamp ordering
    timestamps = [h["timestamp"] for h in result.status_history]
    assert timestamps == sorted(timestamps)

    # Verify user tracking
    acknowledged_entry = [h for h in result.status_history if h["status"] == "doctor_acknowledged"][0]
    assert acknowledged_entry["user_id"] == str(doctor_user)
    assert acknowledged_entry["notes"] == "已处理"


# ── Test 8: alert disabled when CRITICAL_ALERT_ENABLED=False ────────────

@pytest.mark.asyncio
async def test_alert_disabled_when_config_false(
    db_session, patient_with_doctor, monkeypatch,
):
    """When CRITICAL_ALERT_ENABLED is False, no critical alert should be created."""
    monkeypatch.setattr(settings, "CRITICAL_ALERT_ENABLED", False)

    alert = await CriticalAlertService.trigger_critical_alert(
        patient_id=patient_with_doctor,
        alert_type="severe_hyperglycemia",
        value=18.0,
        db=db_session,
    )
    assert alert is None
