"""Structured logging configuration with JSON format for ELK compatibility.

Provides:
- setup_logging() — configure JSON logging with standard fields
- RequestIDMiddleware — inject request_id into logging context + response header
- Structured JSON log formatter
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone

from pythonjsonlogger import jsonlogger

LOG_RECORD_FIELDS = [
    "timestamp",
    "level",
    "service",
    "module",
    "message",
    "request_id",
    "user_id",
    "duration_ms",
]


def _sanitize_message(record: logging.LogRecord) -> str:
    """Ensure message is always a string."""
    msg = record.msg
    if isinstance(msg, str):
        return msg
    if isinstance(msg, dict):
        return str(msg)
    return str(msg)


class _StructuredFormatter(jsonlogger.JsonFormatter):
    """JSON formatter with consistent field ordering."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["service"] = "digital-doctor"
        log_record["module"] = getattr(record, "module_name", record.module)

        extras = getattr(record, "extras", {})
        if isinstance(extras, dict):
            log_record.update(extras)

    def format(self, record):
        record.message = _sanitize_message(record)
        return super().format(record)


def setup_logging(debug: bool = False) -> None:
    """Configure root logger with JSON format.

    In DEBUG mode, also enable console-friendly (text) format.
    """
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if debug:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        handler.setFormatter(_StructuredFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("src").setLevel(level)


class RequestIDMiddleware:
    """ASGI middleware that attaches a unique request_id to every request.

    Injects `request_id` into the logger via a LogRecord filter so every
    log line emitted while handling the request carries the ID.  Also
    sets the ``X-Request-ID`` response header.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        req_id = str(uuid.uuid4())
        scope["request_id"] = req_id

        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            if not hasattr(record, "extras"):
                record.extras = {}
            record.extras.setdefault("request_id", req_id)
            return record

        logging.setLogRecordFactory(record_factory)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append(
                    (b"x-request-id", req_id.encode("ascii"))
                )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logging.setLogRecordFactory(old_factory)
