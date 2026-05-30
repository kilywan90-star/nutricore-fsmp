"""Tests for Celery notification task logic via service functions."""
import uuid
from datetime import datetime, date, timedelta

import pytest
from sqlalchemy import select

from src.models.notification import Notification, NotificationType, NotificationStatus
from src.models.patient import Patient, GlucoseRecord, MedicationReminder
from src.services.notification_service import (
    schedule_medication_reminders_for_all_patients,
    check_glucose_alerts_for_all_patients,
)
from src.services.alert_engine import check_glucose_alerts


@pytest.mark.asyncio
async def test_medication_reminder_task_creates_notifications(db_session):
    """The medication reminder periodic task should create pending notifications for patients with schedules."""
    patient = Patient(
        user_id=uuid.uuid4(),
        name_hash="task_test_patient",
        gender="F",
        birth_year=1975,
        diabetes_type="type2",
    )
    db_session.add(patient)
    await db_session.flush()

    now = datetime.utcnow()
    hour = (now.hour + 3) % 24
    time_str = f"{hour:02d}:00"
    reminder = MedicationReminder(
        patient_id=patient.id,
        drug_name="Glipizide",
        dosage="5mg",
        frequency="daily",
        time_of_day=[time_str],
        start_date=date.today() - timedelta(days=1),
        is_active=True,
    )
    db_session.add(reminder)
    await db_session.commit()

    count = await schedule_medication_reminders_for_all_patients(db_session)
    assert count >= 1

    # Verify at least one pending notification was created
    stmt = select(Notification).where(
        Notification.user_id == patient.user_id,
        Notification.notification_type == NotificationType.MEDICATION_REMINDER,
        Notification.status == NotificationStatus.PENDING,
    )
    result = await db_session.execute(stmt)
    notifications = result.scalars().all()
    assert len(notifications) >= 1


@pytest.mark.asyncio
async def test_glucose_alert_task_creates_alerts(db_session):
    """The glucose alert periodic task should create alert notifications for critical readings."""
    patient = Patient(
        user_id=uuid.uuid4(),
        name_hash="glucose_alert_patient",
        gender="M",
        birth_year=1965,
        diabetes_type="type2",
    )
    db_session.add(patient)
    await db_session.flush()

    # Create a critical hyperglycemia reading
    record = GlucoseRecord(
        patient_id=patient.id,
        value_mmol_l=18.0,
        measure_type="fasting",
        recorded_at=datetime.utcnow(),
    )
    db_session.add(record)
    await db_session.commit()

    count = await check_glucose_alerts_for_all_patients(db_session, check_glucose_alerts)
    assert count >= 1

    # Verify alert notifications were created
    stmt = select(Notification).where(
        Notification.user_id == patient.user_id,
        Notification.notification_type == NotificationType.GLUCOSE_ALERT,
    )
    result = await db_session.execute(stmt)
    notifications = result.scalars().all()
    assert len(notifications) >= 1
    assert "严重高血糖" in notifications[0].title
