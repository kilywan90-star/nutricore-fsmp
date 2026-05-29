import logging
from datetime import datetime
from functools import wraps
from typing import Callable

audit_logger = logging.getLogger("audit")


def log_access(action: str, resource: str, user_id: str = "anonymous"):
    audit_logger.info(
        "AUDIT | %s | %s | %s | %s",
        datetime.utcnow().isoformat(),
        user_id,
        action,
        resource,
    )


def audit(action: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            resource = f"{func.__module__}.{func.__name__}"
            log_access(action, resource)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
