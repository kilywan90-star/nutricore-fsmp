"""Notification service: scheduling, sending, template formatting, and SMS delivery."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, date
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.notification import (
    Notification,
    NotificationTemplate,
    NotificationType,
    NotificationChannel,
    NotificationStatus,
)
from src.models.patient import MedicationReminder, GlucoseRecord, Patient
from src.models.clinical import Alert, AlertSeverity
from src.services.critical_alert_service import CriticalAlertService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template formatting
# ---------------------------------------------------------------------------


def format_template(template: NotificationTemplate, variables: dict[str, str]) -> tuple[str, str]:
    """Fill a NotificationTemplate with variable values; return (title, body)."""
    title = template.title_template
    body = template.body_template
    for key, value in variables.items():
        placeholder = "{" + key + "}"
        title = title.replace(placeholder, value)
        body = body.replace(placeholder, value)
    return title, body


def format_medication_reminder(reminder: MedicationReminder, time_str: str) -> tuple[str, str]:
    """Format a single medication reminder into title/body."""
    title = "用药提醒"
    body = f"该服用 {reminder.drug_name} 了 — {reminder.dosage}，预定时间 {time_str}"
    return title, body


def format_alert_notification(alert: Alert) -> tuple[str, str]:
    """Format a clinical alert into notification title/body."""
    severity_map = {AlertSeverity.CRITICAL: "【紧急】", AlertSeverity.WARNING: "【注意】", AlertSeverity.INFO: ""}
    prefix = severity_map.get(alert.severity, "")
    title = f"{prefix}{alert.title}"
    body = alert.detail
    return title, body


# ---------------------------------------------------------------------------
# Notification scheduling
# ---------------------------------------------------------------------------


async def schedule_medication_reminders(db: AsyncSession, patient_id: UUID) -> list[Notification]:
    """Create Notification records for next 24h of a patient's medication schedule."""
    now = datetime.utcnow()
    end_window = now + timedelta(hours=24)

    # Fetch the patient to get the user_id for the notification FK
    patient_stmt = select(Patient).where(Patient.id == patient_id)
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()
    if not patient or not patient.user_id:
        return []
    user_id = patient.user_id

    stmt = select(MedicationReminder).where(
        MedicationReminder.patient_id == patient_id,
        MedicationReminder.is_active == True,
    )
    result = await db.execute(stmt)
    reminders = result.scalars().all()

    notifications: list[Notification] = []
    for reminder in reminders:
        # Check if medication is within its date range
        today = now.date()
        if reminder.start_date > today:
            continue
        if reminder.end_date and reminder.end_date < today:
            continue

        for time_str in reminder.time_of_day:
            hour, minute = map(int, time_str.split(":"))
            scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if scheduled < now:
                scheduled += timedelta(days=1)
            if scheduled > end_window:
                continue

            title, body = format_medication_reminder(reminder, time_str)
            notification = Notification(
                user_id=user_id,
                notification_type=NotificationType.MEDICATION_REMINDER,
                title=title,
                body=body,
                channel=NotificationChannel.APP,
                scheduled_at=scheduled,
                status=NotificationStatus.PENDING,
                metadata_={"drug_name": reminder.drug_name, "dosage": reminder.dosage, "time": time_str},
            )
            db.add(notification)
            notifications.append(notification)

    if notifications:
        await db.commit()
        logger.info("Scheduled %d medication reminders for patient %s", len(notifications), patient_id)

    return notifications


async def send_pending_notifications(db: AsyncSession) -> list[Notification]:
    """Send all Notification records with status=pending and scheduled_at <= now."""
    now = datetime.utcnow()
    stmt = select(Notification).where(
        Notification.status == NotificationStatus.PENDING,
        Notification.scheduled_at <= now,
    )
    result = await db.execute(stmt)
    pending = result.scalars().all()

    sent: list[Notification] = []
    for notification in pending:
        try:
            _send_via_channel(notification)
            notification.status = NotificationStatus.SENT
            notification.sent_at = now
            sent.append(notification)
        except Exception as exc:
            logger.error("Failed to send notification %s: %s", notification.id, exc)
            notification.status = NotificationStatus.FAILED

    if sent:
        await db.commit()
        logger.info("Sent %d pending notifications", len(sent))

    return sent


def _send_via_channel(notification: Notification) -> None:
    """Dispatch a notification to the appropriate channel (mock for dev)."""
    if notification.channel == NotificationChannel.SMS:
        send_sms("+8600000000000", notification.body)
    elif notification.channel == NotificationChannel.WECHAT:
        logger.info("WeChat push: %s -> %s", notification.title, notification.body)
    else:
        logger.info("App push: %s -> %s", notification.title, notification.body)


def send_sms(phone_number: str, message: str) -> bool:
    """Send SMS via configurable provider. Mock implementation for development."""
    if settings.SMS_PROVIDER == "mock":
        logger.info("Mock SMS to %s: %s", phone_number, message[:50])
        return True
    # Future: integrate with Aliyun SMS, Twilio, etc.
    logger.warning("SMS provider '%s' not implemented, falling back to mock", settings.SMS_PROVIDER)
    logger.info("Mock SMS to %s: %s", phone_number, message[:50])
    return True


# ---------------------------------------------------------------------------
# Doctor alerts
# ---------------------------------------------------------------------------


async def check_and_alert_doctor(db: AsyncSession, patient_id: UUID) -> Notification | None:
    """If a critical alert exists for this patient (unacknowledged), create a doctor Notification."""
    stmt = select(Alert).where(
        Alert.patient_id == patient_id,
        Alert.acknowledged == False,
        Alert.severity == AlertSeverity.CRITICAL,
    ).order_by(Alert.created_at.desc()).limit(1)
    result = await db.execute(stmt)
    critical = result.scalar_one_or_none()

    if not critical:
        return None

    # Check if we already created a notification for this alert
    existing_stmt = select(Notification).where(
        Notification.user_id == patient_id,
        Notification.notification_type == NotificationType.GLUCOSE_ALERT,
        Notification.metadata_["alert_id"].as_string() == str(critical.id),
    )
    existing_result = await db.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        return None

    title, body = format_alert_notification(critical)
    notification = Notification(
        user_id=patient_id,
        notification_type=NotificationType.GLUCOSE_ALERT,
        title=title,
        body=body,
        channel=NotificationChannel.APP,
        scheduled_at=datetime.utcnow(),
        status=NotificationStatus.PENDING,
        metadata_={"alert_id": str(critical.id), "severity": critical.severity.value},
    )
    db.add(notification)
    await db.commit()
    logger.info("Created doctor alert notification for patient %s: %s", patient_id, notification.id)
    return notification


# ---------------------------------------------------------------------------
# Batch operations for scheduled tasks
# ---------------------------------------------------------------------------


async def schedule_medication_reminders_for_all_patients(db: AsyncSession) -> int:
    """Schedule medication reminders for all active patients. Returns count of notifications created."""
    stmt = select(Patient.id).where(Patient.user_id.isnot(None))
    result = await db.execute(stmt)
    patient_ids = [row[0] for row in result.all()]

    total = 0
    for pid in patient_ids:
        notifications = await schedule_medication_reminders(db, pid)
        total += len(notifications)
    return total


async def check_glucose_alerts_for_all_patients(db: AsyncSession, alert_check_fn) -> int:
    """Check glucose alerts for all patients and create Notification records. Returns count of alerts created."""
    stmt = (
        select(GlucoseRecord)
        .order_by(GlucoseRecord.patient_id, GlucoseRecord.recorded_at.desc())
    )
    result = await db.execute(stmt)
    all_records = result.scalars().all()

    # Group by patient_id
    records_by_patient: dict[UUID, list[dict]] = {}
    for r in all_records:
        pid = r.patient_id
        if pid not in records_by_patient:
            records_by_patient[pid] = []
        records_by_patient[pid].append({
            "value_mmol_l": r.value_mmol_l,
            "measure_type": r.measure_type,
            "recorded_at": r.recorded_at,
        })

    # Fetch patient->user_id mapping
    patient_ids = list(records_by_patient.keys())
    patient_stmt = select(Patient.id, Patient.user_id).where(Patient.id.in_(patient_ids))
    patient_result = await db.execute(patient_stmt)
    patient_user_map: dict[UUID, UUID] = {
        row[0]: row[1] for row in patient_result.all() if row[1] is not None
    }

    total = 0
    for patient_id, records in records_by_patient.items():
        user_id = patient_user_map.get(patient_id)
        if not user_id:
            continue
        alerts = alert_check_fn(records)
        for alert_data in alerts:
            notification = Notification(
                user_id=user_id,
                notification_type=NotificationType.GLUCOSE_ALERT,
                title=alert_data["title"],
                body=alert_data["detail"],
                channel=NotificationChannel.APP,
                scheduled_at=datetime.utcnow(),
                status=NotificationStatus.PENDING,
                metadata_={"severity": alert_data["severity"], "alert_type": alert_data["alert_type"]},
            )
            db.add(notification)
            total += 1

            # Trigger critical alert closed-loop for severe events
            if alert_data["severity"] == "critical" and "value" in alert_data:
                await CriticalAlertService.trigger_critical_alert(
                    patient_id=patient_id,
                    alert_type=alert_data["alert_type"],
                    value=alert_data["value"],
                    db=db,
                )

    if total:
        await db.commit()
        logger.info("Created %d glucose alert notifications across %d patients", total, len(records_by_patient))

    return total


async def send_daily_health_tip(db: AsyncSession) -> int:
    """Send daily health tip to all active patients. Returns count of tips sent."""
    stmt = select(Patient.id, Patient.user_id).where(Patient.user_id.isnot(None))
    result = await db.execute(stmt)
    patient_user_pairs = [(row[0], row[1]) for row in result.all()]

    tips = [
        "今日健康提示：每天步行30分钟有助于血糖控制，尝试饭后散步15分钟。",
        "今日健康提示：合理搭配主食，粗细粮比例建议1:1，每餐主食量约拳头大小。",
        "今日健康提示：血糖监测请保持规律，空腹和餐后2小时血糖都要记录哦。",
        "今日健康提示：保持充足睡眠（7-8小时）对血糖管理很重要，今晚早点休息吧。",
        "今日健康提示：多喝水有助于代谢，每天建议饮水1500-2000ml。",
        "今日健康提示：用药请遵医嘱，不要随意调整剂量或停药，如有不适及时咨询医生。",
        "今日健康提示：定期复查HbA1c（每3-6个月），了解血糖长期控制状况。",
    ]
    tip_index = datetime.utcnow().day % len(tips)
    tip_body = tips[tip_index]

    total = 0
    for pid, user_id in patient_user_pairs:
        notification = Notification(
            user_id=user_id,
            notification_type=NotificationType.HEALTH_TIP,
            title="每日健康提示",
            body=tip_body,
            channel=NotificationChannel.APP,
            scheduled_at=datetime.utcnow(),
            status=NotificationStatus.PENDING,
        )
        db.add(notification)
        total += 1

    if total:
        await db.commit()
        logger.info("Sent daily health tip to %d patients", total)

    return total


async def cleanup_old_notifications(db: AsyncSession) -> int:
    """Delete notifications older than NOTIFICATION_CLEANUP_DAYS. Returns count deleted."""
    cutoff = datetime.utcnow() - timedelta(days=settings.NOTIFICATION_CLEANUP_DAYS)
    stmt = delete(Notification).where(
        Notification.scheduled_at < cutoff,
        Notification.status.in_([NotificationStatus.SENT, NotificationStatus.READ, NotificationStatus.FAILED]),
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount
    if count:
        logger.info("Cleaned up %d old notifications (older than %s)", count, cutoff.isoformat())
    return count
