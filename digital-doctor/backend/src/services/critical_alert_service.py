"""Critical alert closed-loop service — 3-tier escalation (lightweight/standard/complete)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.critical_alert import CriticalAlert, CriticalAlertStatus
from src.models.org import DoctorProfile, PatientAssignment
from src.models.user import User

logger = logging.getLogger(__name__)


class CriticalAlertService:

    @staticmethod
    async def trigger_critical_alert(
        patient_id: UUID,
        alert_type: str,
        value: float,
        db: AsyncSession,
    ) -> CriticalAlert | None:
        """Create a critical alert and begin the closed-loop workflow."""
        if not settings.CRITICAL_ALERT_ENABLED:
            return None

        title_map = {
            "severe_hyperglycemia": "严重高血糖预警",
            "hypoglycemia": "低血糖预警",
        }
        detail_map = {
            "severe_hyperglycemia": f"血糖{value}mmol/L>=16.7，需立即处理",
            "hypoglycemia": f"血糖{value}mmol/L<=3.9，低血糖",
        }

        # Find the assigned doctor
        doctor_stmt = (
            select(User.id)
            .join(DoctorProfile, DoctorProfile.user_id == User.id)
            .join(
                PatientAssignment,
                PatientAssignment.doctor_id == DoctorProfile.id,
            )
            .where(
                PatientAssignment.patient_id == patient_id,
                PatientAssignment.is_active == True,
                DoctorProfile.is_active == True,
            )
            .limit(1)
        )
        doctor_result = await db.execute(doctor_stmt)
        doctor_row = doctor_result.first()
        doctor_user_id = doctor_row[0] if doctor_row else None

        alert = CriticalAlert(
            patient_id=patient_id,
            alert_type=alert_type,
            severity="critical",
            title=title_map.get(alert_type, alert_type),
            detail=detail_map.get(alert_type, f"血糖{value}mmol/L"),
            value=value,
            doctor_user_id=doctor_user_id,
            status=CriticalAlertStatus.DETECTED,
            status_history=[
                {
                    "status": CriticalAlertStatus.DETECTED.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": None,
                    "notes": "自动检测触发",
                }
            ],
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        mode = settings.CLOSED_LOOP_MODE

        if mode == "lightweight":
            await CriticalAlertService._notify_doctor(alert, db)
        elif mode == "standard":
            await CriticalAlertService._notify_doctor(alert, db)
            await CriticalAlertService._send_to_lis(alert)
        elif mode == "complete":
            await CriticalAlertService._notify_doctor(alert, db)
            await CriticalAlertService._send_to_lis(alert)
            await CriticalAlertService._notify_patient(alert)

        logger.info(
            "Critical alert triggered: patient=%s type=%s value=%s mode=%s",
            patient_id, alert_type, value, mode,
        )
        return alert

    @staticmethod
    async def doctor_acknowledge(
        alert_id: UUID,
        doctor_id: UUID,
        resolution: str | None,
        db: AsyncSession,
    ) -> CriticalAlert | None:
        """Doctor acknowledges a critical alert. In standard/complete mode, triggers nurse confirmation after."""
        stmt = select(CriticalAlert).where(CriticalAlert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        history = list(alert.status_history or [])
        history.append({
            "status": CriticalAlertStatus.DOCTOR_ACKNOWLEDGED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(doctor_id),
            "notes": resolution or "",
        })

        alert.status = CriticalAlertStatus.DOCTOR_ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = doctor_id
        alert.resolution = resolution
        alert.status_history = history

        mode = settings.CLOSED_LOOP_MODE

        if resolution == "已处理":
            # Doctor handled it directly — resolve
            return await CriticalAlertService._resolve_alert(alert, doctor_id, db)
        elif resolution == "已联系患者":
            # In lightweight mode, this resolves; in standard/complete, it goes to nurse confirm
            if mode == "lightweight":
                return await CriticalAlertService._resolve_alert(alert, doctor_id, db)
            elif mode in ("standard", "complete"):
                # Trigger nurse confirmation flow
                history.append({
                    "status": "awaiting_nurse_confirmation",
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": str(doctor_id),
                    "notes": "等待护士确认",
                })
                alert.status_history = history
                await db.commit()
                await db.refresh(alert)
                return alert
        elif resolution == "转急诊":
            # Escalate immediately
            return await CriticalAlertService._resolve_alert(alert, doctor_id, db)

        await db.commit()
        await db.refresh(alert)
        return alert

    @staticmethod
    async def nurse_confirm(
        alert_id: UUID,
        nurse_id: UUID,
        db: AsyncSession,
    ) -> CriticalAlert | None:
        """Nurse confirms the alert (standard mode). In complete mode, triggers patient notification."""
        stmt = select(CriticalAlert).where(CriticalAlert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        history = list(alert.status_history or [])
        history.append({
            "status": CriticalAlertStatus.NURSE_CONFIRMED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(nurse_id),
            "notes": "护士确认",
        })

        alert.status = CriticalAlertStatus.NURSE_CONFIRMED
        alert.status_history = history

        mode = settings.CLOSED_LOOP_MODE

        if mode == "standard":
            await CriticalAlertService._resolve_alert(alert, None, db)
        elif mode == "complete":
            await CriticalAlertService._notify_patient(alert)
            history2 = alert.status_history or []
            history2.append({
                "status": CriticalAlertStatus.PATIENT_NOTIFIED.value,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": None,
                "notes": "已通知患者",
            })
            alert.status = CriticalAlertStatus.PATIENT_NOTIFIED
            alert.status_history = history2
            await CriticalAlertService._resolve_alert(alert, None, db)

        await db.commit()
        await db.refresh(alert)
        return alert

    @staticmethod
    async def escalate(alert_id: UUID, db: AsyncSession) -> CriticalAlert | None:
        """Escalate an unacknowledged alert to the department head."""
        stmt = select(CriticalAlert).where(CriticalAlert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return None

        # Find department head
        if alert.doctor_user_id:
            dept_head_stmt = (
                select(User.id)
                .join(DoctorProfile, DoctorProfile.user_id == User.id)
                .where(
                    DoctorProfile.is_department_head == True,
                    DoctorProfile.is_active == True,
                )
                .limit(1)
            )
        else:
            dept_head_stmt = (
                select(User.id)
                .join(DoctorProfile, DoctorProfile.user_id == User.id)
                .where(
                    DoctorProfile.is_department_head == True,
                    DoctorProfile.is_active == True,
                )
                .limit(1)
            )
        dept_result = await db.execute(dept_head_stmt)
        dept_row = dept_result.first()
        escalated_to = dept_row[0] if dept_row else None

        history = list(alert.status_history or [])
        history.append({
            "status": CriticalAlertStatus.ESCALATED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": None,
            "notes": f"超时未确认，自动升级至科室负责人 {str(escalated_to) if escalated_to else 'N/A'}",
        })

        alert.status = CriticalAlertStatus.ESCALATED
        alert.escalated_to = escalated_to
        alert.status_history = history

        await db.commit()
        await db.refresh(alert)
        logger.warning(
            "Critical alert escalated: alert=%s patient=%s escalated_to=%s",
            alert_id, alert.patient_id, escalated_to,
        )
        return alert

    @staticmethod
    async def resolve(alert_id: UUID, db: AsyncSession) -> CriticalAlert | None:
        """Manually resolve a critical alert."""
        stmt = select(CriticalAlert).where(CriticalAlert.id == alert_id)
        result = await db.execute(stmt)
        alert = result.scalar_one_or_none()
        if not alert:
            return None
        return await CriticalAlertService._resolve_alert(alert, None, db)

    @staticmethod
    async def check_timeouts(db: AsyncSession) -> dict:
        """Check for alerts that have exceeded ack timeout and escalate them.
        Called periodically (every 5 minutes) by Celery beat."""
        timeout = timedelta(minutes=settings.LIGHTWEIGHT_ACK_TIMEOUT_MINUTES)
        cutoff = datetime.utcnow() - timeout

        stmt = select(CriticalAlert.id).where(
            CriticalAlert.status.in_([
                CriticalAlertStatus.DETECTED,
                CriticalAlertStatus.NOTIFIED_DOCTOR,
            ]),
            CriticalAlert.detected_at < cutoff,
        )
        result = await db.execute(stmt)
        escalate_ids = [row[0] for row in result.all()]

        escalated_count = 0
        for alert_id in escalate_ids:
            await CriticalAlertService.escalate(alert_id, db)
            escalated_count += 1

        # Also check for EXPIRED status alerts older than escalate-after
        escalate_timeout = timedelta(minutes=settings.LIGHTWEIGHT_ESCALATE_AFTER_MINUTES)
        escalate_cutoff = datetime.utcnow() - escalate_timeout

        expired_stmt = select(CriticalAlert.id).where(
            CriticalAlert.status == CriticalAlertStatus.ESCALATED,
            CriticalAlert.detected_at < escalate_cutoff,
        )
        expired_result = await db.execute(expired_stmt)
        mark_expired_ids = [row[0] for row in expired_result.all()]

        expired_count = 0
        for alert_id in mark_expired_ids:
            stmt2 = select(CriticalAlert).where(CriticalAlert.id == alert_id)
            r2 = await db.execute(stmt2)
            alert = r2.scalar_one_or_none()
            if alert:
                history = list(alert.status_history or [])
                history.append({
                    "status": CriticalAlertStatus.EXPIRED.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user_id": None,
                    "notes": f"升级后{settings.LIGHTWEIGHT_ESCALATE_AFTER_MINUTES}分钟仍未处理，标记为过期",
                })
                alert.status = CriticalAlertStatus.EXPIRED
                alert.status_history = history
                expired_count += 1

        if expired_count:
            await db.commit()

        return {"escalated": escalated_count, "expired": expired_count}

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    async def _notify_doctor(alert: CriticalAlert, db: AsyncSession) -> None:
        """Mark doctor as notified (status transition)."""
        history = list(alert.status_history or [])
        history.append({
            "status": CriticalAlertStatus.NOTIFIED_DOCTOR.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(alert.doctor_user_id) if alert.doctor_user_id else None,
            "notes": "已通知医生",
        })
        alert.status = CriticalAlertStatus.NOTIFIED_DOCTOR
        alert.status_history = history
        await db.commit()
        await db.refresh(alert)
        logger.info("Critical alert %s: doctor notified", alert.id)

    @staticmethod
    async def _send_to_lis(alert: CriticalAlert) -> None:
        """Send alert to LIS system (mock for dev)."""
        if settings.STANDARD_LIS_ENDPOINT:
            logger.info(
                "Critical alert %s: sent to LIS endpoint %s",
                alert.id, settings.STANDARD_LIS_ENDPOINT,
            )
        else:
            logger.info("Critical alert %s: LIS integration skipped (no endpoint configured)", alert.id)

    @staticmethod
    async def _notify_patient(alert: CriticalAlert) -> None:
        """Notify patient via SMS/phone (mock for dev)."""
        if settings.COMPLETE_PATIENT_SMS_ENABLED:
            logger.info("Critical alert %s: SMS notification sent to patient %s", alert.id, alert.patient_id)
        if settings.COMPLETE_PATIENT_PHONE_ENABLED:
            logger.info("Critical alert %s: phone call triggered for patient %s", alert.id, alert.patient_id)
        if settings.COMPLETE_EMERGENCY_NAVIGATION_ENABLED:
            logger.info("Critical alert %s: emergency navigation enabled for patient %s", alert.id, alert.patient_id)

    @staticmethod
    async def _resolve_alert(
        alert: CriticalAlert,
        user_id: UUID | None,
        db: AsyncSession,
    ) -> CriticalAlert:
        """Mark alert as RESOLVED and record in history."""
        history = list(alert.status_history or [])
        history.append({
            "status": CriticalAlertStatus.RESOLVED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id) if user_id else None,
            "notes": "已处理",
        })
        alert.status = CriticalAlertStatus.RESOLVED
        alert.closed_at = datetime.utcnow()
        alert.status_history = history
        await db.commit()
        await db.refresh(alert)
        logger.info("Critical alert %s: resolved", alert.id)
        return alert
