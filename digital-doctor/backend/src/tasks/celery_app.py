"""Celery app instance with Redis broker, JSON serialization, and beat schedule."""
from celery import Celery
from celery.schedules import crontab

from src.config import settings

celery_app = Celery(
    "digital_doctor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "send-medication-reminders": {
            "task": "src.tasks.notification_tasks.send_medication_reminders",
            "schedule": 300.0,  # every 5 minutes
        },
        "check-glucose-alerts": {
            "task": "src.tasks.notification_tasks.check_glucose_alerts",
            "schedule": 900.0,  # every 15 minutes
        },
        "daily-health-tip": {
            "task": "src.tasks.notification_tasks.daily_health_tip",
            "schedule": crontab(hour=9, minute=0),  # daily at 9am
        },
        "cleanup-old-notifications": {
            "task": "src.tasks.notification_tasks.cleanup_old_notifications",
            "schedule": crontab(hour=3, minute=0),  # daily at 3am
        },
    },
)
