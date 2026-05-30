"""Tests for notification service."""
import uuid
from datetime import datetime, date, timedelta

import pytest
from sqlalchemy import select

from src.models.notification import (
    Notification,
    NotificationTemplate,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)
from src.models.patient import Patient, MedicationReminder
from src.models.clinical import Alert, AlertSeverity
from src.services.notification_service import (
    schedule_medication_reminders,
    send_pending_notifications,
    format_medication_reminder,
    format_alert_notification,
)


@pytest.mark.asyncio
async def test_schedule_medication_reminders(db_session):
    """Medication reminders should be scheduled for next 24h windows."""
    patient = Patient(
        user_id=uuid.uuid4(),
        name_hash="test_patient",
        gender="M",
        birth_year=1980,
        diabetes_type="type2",
    )
    db_session.add(patient)
    await db_session.flush()

    now = datetime.utcnow()
    # Create a reminder with a time_of_day that falls within the next 24h
    hour = (now.hour + 2) % 24
    time_str = f"{hour:02d}:30"
    reminder = MedicationReminder(
        patient_id=patient.id,
        drug_name="Metformin",
        dosage="500mg",
        frequency="daily",
        time_of_day=[time_str],
        start_date=date.today() - timedelta(days=7),
        is_active=True,
    )
    db_session.add(reminder)
    await db_session.commit()

    notifications = await schedule_medication_reminders(db_session, patient.id)
    assert len(notifications) >= 1
    assert notifications[0].notification_type == NotificationType.MEDICATION_REMINDER
    assert notifications[0].title == "用药提醒"
    assert "Metformin" in notifications[0].body


@pytest.mark.asyncio
async def test_send_pending_notifications(db_session):
    """Pending notifications with scheduled_at <= now should be sent."""
    notification = Notification(
        user_id=uuid.uuid4(),
        notification_type=NotificationType.HEALTH_TIP,
        title="Test Tip",
        body="This is a test health tip.",
        channel=NotificationChannel.APP,
        scheduled_at=datetime.utcnow() - timedelta(minutes=5),
        status=NotificationStatus.PENDING,
    )
    db_session.add(notification)
    await db_session.commit()

    sent = await send_pending_notifications(db_session)
    assert len(sent) == 1
    assert sent[0].status == NotificationStatus.SENT
    assert sent[0].sent_at is not None


def test_format_medication_reminder():
    """Medication reminder formatting should produce correct title/body."""
    reminder = MedicationReminder(
        drug_name="Insulin",
        dosage="10 units",
        frequency="daily",
        time_of_day=["08:00"],
        start_date=date.today(),
    )
    title, body = format_medication_reminder(reminder, "08:00")
    assert "用药提醒" == title
    assert "Insulin" in body
    assert "10 units" in body


def test_format_alert_notification():
    """Alert notification formatting should include severity prefix and detail."""
    alert = Alert(
        patient_id=uuid.uuid4(),
        alert_type="severe_hyperglycemia",
        severity=AlertSeverity.CRITICAL,
        title="严重高血糖预警",
        detail="血糖18.0mmol/L，需立即处理",
    )
    title, body = format_alert_notification(alert)
    assert "紧急" in title
    assert "严重高血糖预警" in title
    assert "18.0" in body
