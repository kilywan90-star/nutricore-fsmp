"""FastAPI middleware for automatic HTTP request metrics tracking.

Provides:
- http_metrics_middleware — callable that records request count + duration
- Excludes /health* and /metrics paths
"""

from __future__ import annotations

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.services.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)

EXCLUDED_PREFIXES: tuple[str, ...] = ("/health", "/metrics")


def _normalize_path(path: str) -> str:
    """Group numeric path segments into {id} for cardinality control."""
    parts = path.split("/")
    normalized = []
    for p in parts:
        normalized.append("{id}" if p.isdigit() else p)
    return "/".join(normalized)


class MetricsTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware that records HTTP request count and duration metrics."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip excluded paths to avoid noise
        if any(path.startswith(p) for p in EXCLUDED_PREFIXES):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed = time.monotonic() - start

        endpoint = _normalize_path(path)
        method = request.method

        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(response.status_code),
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(elapsed)

        return response
