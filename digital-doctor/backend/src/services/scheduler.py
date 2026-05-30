"""Fallback scheduler using APScheduler for when Celery/Redis is unavailable.

Auto-detects whether Celery broker is reachable. If not, starts an in-process
APScheduler to run notification periodic tasks in a background thread.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.config import settings
from src.db.session import async_session_factory
from src.services.notification_service import (
    schedule_medication_reminders_for_all_patients,
    send_pending_notifications,
    check_glucose_alerts_for_all_patients,
    send_daily_health_tip,
    cleanup_old_notifications,
)
from src.services.alert_engine import check_glucose_alerts

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_started: bool = False


def _check_celery_available() -> bool:
    """Quick check if Redis broker is reachable."""
    try:
        import redis
        r = redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        logger.info("Celery broker not reachable, using APScheduler fallback")
        return False


def _run_async_sync(coro):
    """Run an async coroutine from synchronous context."""
    try:
        return asyncio.run(coro)
    except Exception as exc:
        logger.error("Scheduler task failed: %s", exc)


def _medication_reminder_job():
    """Scheduled job: medication reminders every 5 minutes."""
    async def _run():
        async with async_session_factory() as db:
            count = await schedule_medication_reminders_for_all_patients(db)
            sent = await send_pending_notifications(db)
            logger.info("Scheduler: created %d med reminders, sent %d", count, len(sent))

    _run_async_sync(_run())


def _glucose_alert_job():
    """Scheduled job: glucose alerts every 15 minutes."""
    async def _run():
        async with async_session_factory() as db:
            count = await check_glucose_alerts_for_all_patients(db, check_glucose_alerts)
            await send_pending_notifications(db)
            logger.info("Scheduler: created %d glucose alerts", count)

    _run_async_sync(_run())


def _daily_health_tip_job():
    """Scheduled job: daily health tip at 9am."""
    async def _run():
        async with async_session_factory() as db:
            count = await send_daily_health_tip(db)
            await send_pending_notifications(db)
            logger.info("Scheduler: sent daily tip to %d patients", count)

    _run_async_sync(_run())


def _cleanup_job():
    """Scheduled job: cleanup old notifications at 3am."""
    async def _run():
        async with async_session_factory() as db:
            count = await cleanup_old_notifications(db)
            logger.info("Scheduler: cleaned up %d old notifications", count)

    _run_async_sync(_run())


def start_scheduler() -> bool:
    """Start the fallback APScheduler if Celery is not available.

    Returns True if the scheduler was started, False if Celery is available.
    """
    global _scheduler, _started
    if _started:
        return True

    if _check_celery_available():
        logger.info("Celery is available — skipping APScheduler fallback")
        return False

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _medication_reminder_job,
        trigger=IntervalTrigger(minutes=5),
        id="medication_reminders",
        name="Medication reminders",
        replace_existing=True,
    )
    _scheduler.add_job(
        _glucose_alert_job,
        trigger=IntervalTrigger(minutes=15),
        id="glucose_alerts",
        name="Glucose alerts",
        replace_existing=True,
    )
    _scheduler.add_job(
        _daily_health_tip_job,
        trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Shanghai"),
        id="daily_health_tip",
        name="Daily health tip",
        replace_existing=True,
    )
    _scheduler.add_job(
        _cleanup_job,
        trigger=CronTrigger(hour=3, minute=0, timezone="Asia/Shanghai"),
        id="cleanup_notifications",
        name="Cleanup old notifications",
        replace_existing=True,
    )
    _scheduler.start()
    _started = True
    logger.info("APScheduler fallback started with 4 jobs")
    return True


def stop_scheduler() -> None:
    """Graceful shutdown of the APScheduler."""
    global _scheduler, _started
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        _started = False
        logger.info("APScheduler stopped")
