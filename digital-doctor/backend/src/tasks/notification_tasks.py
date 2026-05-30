"""Celery periodic tasks for push notifications."""
import asyncio
import logging

from src.tasks.celery_app import celery_app
from src.db.session import async_session_factory
from src.services.notification_service import (
    schedule_medication_reminders_for_all_patients,
    send_pending_notifications,
    check_glucose_alerts_for_all_patients,
    send_daily_health_tip,
    cleanup_old_notifications,
)
from src.services.alert_engine import check_glucose_alerts as check_alerts_fn

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # Already inside an event loop — create a new one in a thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


@celery_app.task(name="src.tasks.notification_tasks.send_medication_reminders")
def send_medication_reminders():
    """Run every 5 minutes: query medication schedules, create pending notifications, send them."""
    async def _run():
        async with async_session_factory() as db:
            count = await schedule_medication_reminders_for_all_patients(db)
            logger.info("Medication reminder task: created %d notifications", count)
            sent = await send_pending_notifications(db)
            logger.info("Medication reminder task: sent %d pending notifications", len(sent))
            return {"created": count, "sent": len(sent)}

    return _run_async(_run())


@celery_app.task(name="src.tasks.notification_tasks.check_glucose_alerts")
def check_glucose_alerts():
    """Run every 15 minutes: check recent glucose records for all patients, create alerts."""
    async def _run():
        async with async_session_factory() as db:
            count = await check_glucose_alerts_for_all_patients(db, check_alerts_fn)
            await send_pending_notifications(db)
            logger.info("Glucose alert task: created %d alert notifications", count)
            return {"alerts_created": count}

    return _run_async(_run())


@celery_app.task(name="src.tasks.notification_tasks.daily_health_tip")
def daily_health_tip():
    """Run daily at 9am: send health tip to all active patients."""
    async def _run():
        async with async_session_factory() as db:
            count = await send_daily_health_tip(db)
            await send_pending_notifications(db)
            logger.info("Daily health tip task: sent to %d patients", count)
            return {"tips_sent": count}

    return _run_async(_run())


@celery_app.task(name="src.tasks.notification_tasks.cleanup_old_notifications")
def cleanup_old_notifications():
    """Run daily at 3am: delete notifications older than 90 days."""
    async def _run():
        async with async_session_factory() as db:
            count = await cleanup_old_notifications(db)
            logger.info("Cleanup task: deleted %d old notifications", count)
            return {"deleted": count}

    return _run_async(_run())
