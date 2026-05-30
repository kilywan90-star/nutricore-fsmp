"""Celery periodic task for critical alert closed-loop timeout checks."""
import asyncio
import logging

from src.tasks.celery_app import celery_app
from src.db.session import async_session_factory
from src.services.critical_alert_service import CriticalAlertService

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


@celery_app.task(name="src.tasks.critical_alert_tasks.check_critical_alert_timeouts")
def check_critical_alert_timeouts():
    """Run every 5 minutes: escalate alerts older than ACK_TIMEOUT that haven't been acknowledged."""
    async def _run():
        async with async_session_factory() as db:
            result = await CriticalAlertService.check_timeouts(db)
            logger.info(
                "Critical alert timeout check: escalated %d, expired %d",
                result["escalated"], result["expired"],
            )
            return result

    return _run_async(_run())
