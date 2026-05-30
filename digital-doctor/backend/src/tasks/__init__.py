try:
    from src.tasks.celery_app import celery_app
except ImportError:
    celery_app = None
