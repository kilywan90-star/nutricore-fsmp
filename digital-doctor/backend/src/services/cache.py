"""
Redis caching layer with graceful degradation.

Provides a CacheManager singleton and a @cache_decorator for async functions.
If Redis is unavailable, cache operations become no-ops — the application
continues without caching rather than failing.

TTL reference:
    Patient list:              60 seconds
    Lab report interpretations: 300 seconds (5 min)
    Rule engine results:        3600 seconds (1 hour)
    Department stats:           120 seconds (2 min)

Usage:
    from src.services.cache import cache_manager

    data = await cache_manager.get_or_set(
        "patients:list:page1",
        ttl_seconds=60,
        fetch_fn=lambda: get_patient_list(db, page=1),
    )

    await cache_manager.invalidate("patients:list:*")

    @cache_decorator(ttl_seconds=300)
    async def interpret_lab(report_id):
        ...
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Awaitable, Callable

from redis.asyncio import Redis

from src.config import settings

logger = logging.getLogger("performance.cache")

_DEFAULT_TTL = 300  # 5 minutes fallback


class CacheManager:
    """Async Redis-backed cache manager.

    All methods are safe to call even when Redis is down — they degrade
    to no-ops (get_or_set falls through to fetch_fn, invalidate does nothing).
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis: Redis | None = None
        self._redis_url = redis_url or settings.REDIS_URL
        self._available: bool | None = None  # None = not checked yet

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _ensure_connection(self) -> Redis | None:
        if self._available is False:
            return None
        if self._redis is not None:
            return self._redis
        try:
            self._redis = Redis.from_url(self._redis_url, socket_connect_timeout=2)
            await self._redis.ping()
            self._available = True
            return self._redis
        except Exception:
            logger.warning("Redis unavailable at %s — caching disabled", self._redis_url)
            self._available = False
            self._redis = None
            return None

    @property
    async def available(self) -> bool:
        r = await self._ensure_connection()
        return r is not None

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def get_or_set(
        self,
        key: str,
        ttl_seconds: int = _DEFAULT_TTL,
        fetch_fn: Callable[[], Awaitable[Any]] | None = None,
    ) -> Any | None:
        """Fetch value from cache by key. On miss, compute via fetch_fn,
        store the result in Redis with the given TTL, and return it.

        Returns None only when both cache miss and no fetch_fn is provided.
        Gracefully falls through to fetch_fn if Redis is unavailable.
        """
        redis = await self._ensure_connection()

        # Try cache read
        if redis is not None:
            try:
                raw = await redis.get(key)
                if raw is not None:
                    return json.loads(raw)
            except Exception as exc:
                logger.warning("Cache read error for key=%s: %s", key, exc)

        # Cache miss or Redis down — compute
        if fetch_fn is None:
            return None

        value = await fetch_fn()

        # Store in cache
        if redis is not None and value is not None:
            try:
                await redis.setex(key, ttl_seconds, json.dumps(value, default=str))
            except Exception as exc:
                logger.warning("Cache write error for key=%s: %s", key, exc)

        return value

    async def get(self, key: str) -> Any | None:
        """Direct cache read without fallback computation."""
        redis = await self._ensure_connection()
        if redis is None:
            return None
        try:
            raw = await redis.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Cache get error for key=%s: %s", key, exc)
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = _DEFAULT_TTL) -> bool:
        """Write a value to the cache. Returns True on success, False on failure."""
        redis = await self._ensure_connection()
        if redis is None:
            return False
        try:
            await redis.setex(key, ttl_seconds, json.dumps(value, default=str))
            return True
        except Exception as exc:
            logger.warning("Cache set error for key=%s: %s", key, exc)
            return False

    async def invalidate(self, pattern: str) -> int:
        """Delete all keys matching a Redis glob pattern (e.g. ``patients:list:*``).

        Returns the number of keys deleted, or 0 if Redis is unavailable.
        """
        redis = await self._ensure_connection()
        if redis is None:
            return 0
        try:
            # SCAN avoids blocking Redis on large key sets
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await redis.delete(*keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as exc:
            logger.warning("Cache invalidate error for pattern=%s: %s", pattern, exc)
            return 0

    async def delete(self, key: str) -> bool:
        """Delete a single key. Returns True if key was deleted, False otherwise."""
        redis = await self._ensure_connection()
        if redis is None:
            return False
        try:
            result = await redis.delete(key)
            return result > 0
        except Exception as exc:
            logger.warning("Cache delete error for key=%s: %s", key, exc)
            return False

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
            self._available = None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

cache_manager = CacheManager()


# ---------------------------------------------------------------------------
# Decorator — caches async function results by (func_name, args, kwargs)
# ---------------------------------------------------------------------------


def cache_decorator(ttl_seconds: int = _DEFAULT_TTL):
    """Decorator that caches the return value of an async function in Redis.

    The cache key is derived from the function name, args, and kwargs.
    On cache hit the function body is skipped entirely. On cache miss
    the function executes and its result is stored with the given TTL.

    If Redis is unavailable, the function executes without caching
    (graceful degradation).

    Usage:
        @cache_decorator(ttl_seconds=300)
        async def interpret_lab_report(report_id: str) -> dict:
            ...
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            manager = cache_manager

            # Build deterministic cache key
            key_parts = [func.__module__, func.__qualname__]
            for arg in args:
                key_parts.append(str(arg))
            for k in sorted(kwargs):
                key_parts.append(f"{k}={kwargs[k]}")
            key = f"decorator:{':'.join(key_parts)}"

            async def compute_and_cache():
                result = await func(*args, **kwargs)
                return result

            return await manager.get_or_set(
                key,
                ttl_seconds=ttl_seconds,
                fetch_fn=compute_and_cache,
            )

        return wrapper

    return decorator
