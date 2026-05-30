"""Health check service — database, Redis, LLM, disk, system aggregate.

Each check catches its own exceptions to enable graceful degradation.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx
from redis.asyncio import Redis

from src.config import settings
from src.db.session import engine

logger = logging.getLogger(__name__)

HEALTH_GRACE_MS = 200  # threshold for suboptimal but not failing


@dataclass
class CheckResult:
    status: str  # "healthy" | "degraded" | "unhealthy"
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def _health_status(ok: bool, latency_ms: float) -> str:
    if not ok:
        return "unhealthy"
    if latency_ms > HEALTH_GRACE_MS:
        return "degraded"
    return "healthy"


async def check_database() -> CheckResult:
    """Ping PostgreSQL via raw SQL. Returns latency and status."""
    from sqlalchemy import text

    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return CheckResult(
            status=_health_status(True, latency),
            latency_ms=round(latency, 2),
            message="Database reachable",
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.error("Database health check failed: %s", exc)
        return CheckResult(
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Database unreachable: {exc}",
        )


async def check_redis() -> CheckResult:
    """Ping Redis. Returns latency and status."""
    start = time.monotonic()
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        await r.aclose()
        latency = (time.monotonic() - start) * 1000
        return CheckResult(
            status=_health_status(True, latency),
            latency_ms=round(latency, 2),
            message="Redis reachable",
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.error("Redis health check failed: %s", exc)
        return CheckResult(
            status="unhealthy",
            latency_ms=round(latency, 2),
            message=f"Redis unreachable: {exc}",
        )


async def check_llm() -> CheckResult:
    """Lightweight connectivity ping to LLM API (no inference)."""
    if not settings.LLM_API_KEY:
        return CheckResult(
            status="degraded",
            message="LLM API key not configured",
        )

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.LLM_BASE_URL}/models",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            )
        latency = (time.monotonic() - start) * 1000
        if resp.status_code == 200:
            return CheckResult(
                status=_health_status(True, latency),
                latency_ms=round(latency, 2),
                message="LLM API reachable",
            )
        return CheckResult(
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"LLM API returned {resp.status_code}",
        )
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        logger.error("LLM health check failed: %s", exc)
        return CheckResult(
            status="degraded",
            latency_ms=round(latency, 2),
            message=f"LLM API unreachable: {exc}",
        )


def check_disk_space() -> CheckResult:
    """Check available disk space on the data volume."""
    from src.services.metrics import disk_free_pct_gauge

    try:
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        pct_free = (usage.free / usage.total) * 100

        # Update Prometheus gauge
        disk_free_pct_gauge.set(pct_free)

        if pct_free < 10:
            status = "unhealthy"
        elif pct_free < 20:
            status = "degraded"
        else:
            status = "healthy"

        return CheckResult(
            status=status,
            message=f"Disk {free_gb:.1f} GB free of {total_gb:.1f} GB ({pct_free:.1f}%)",
            details={"free_gb": round(free_gb, 2), "total_gb": round(total_gb, 2), "pct_free": round(pct_free, 1)},
        )
    except Exception as exc:
        logger.error("Disk health check failed: %s", exc)
        return CheckResult(
            status="unhealthy",
            message=f"Disk check failed: {exc}",
        )


async def system_health() -> dict[str, Any]:
    """Aggregate all health checks. Returns system-level status.

    Status rules:
    - "healthy" — all checks healthy or degraded
    - "degraded" — at least one check degraded, none unhealthy
    - "unhealthy" — at least one check unhealthy
    """
    results: dict[str, CheckResult] = {}

    # Run checks concurrently where possible
    db_task = asyncio.create_task(check_database())
    redis_task = asyncio.create_task(check_redis())
    llm_task = asyncio.create_task(check_llm())

    # disk check is synchronous; run in thread
    disk_result = await asyncio.to_thread(check_disk_space)
    results["disk"] = disk_result

    results["database"] = await db_task
    results["redis"] = await redis_task
    results["llm"] = await llm_task

    statuses = {r.status for r in results.values()}

    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    logger.info(
        "System health: %s | db=%s redis=%s llm=%s disk=%s",
        overall,
        results["database"].status,
        results["redis"].status,
        results["llm"].status,
        results["disk"].status,
    )

    return {
        "status": overall,
        "checks": {name: r.__dict__ for name, r in results.items()},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
