"""Tests for Redis caching layer with graceful degradation."""
import json

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.cache import CacheManager, cache_decorator, cache_manager


class TestCacheHit:
    """Verify cache returns stored value on hit without calling fetch_fn."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value(self):
        mgr = CacheManager(redis_url="redis://localhost:6379/0")
        cache_key = "test:hit:1"
        cached_data = {"result": "cached_value", "count": 42}

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

        with patch.object(mgr, "_ensure_connection", AsyncMock(return_value=mock_redis)):
            fetch_called = False

            async def fetch_fn():
                nonlocal fetch_called
                fetch_called = True
                return {"result": "fresh"}

            value = await mgr.get_or_set(cache_key, ttl_seconds=60, fetch_fn=fetch_fn)
            assert value == cached_data
            assert fetch_called is False
            mock_redis.get.assert_awaited_once_with(cache_key)

        await mgr.close()

    @pytest.mark.asyncio
    async def test_cache_miss_calls_fetch_and_stores(self):
        """On cache miss, fetch_fn is called and the result is stored in Redis."""
        mgr = CacheManager(redis_url="redis://localhost:6379/0")
        cache_key = "test:miss:1"
        fresh_data = {"result": "computed_fresh", "count": 99}

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)  # cache miss
        mock_redis.setex = AsyncMock(return_value=True)

        with patch.object(mgr, "_ensure_connection", AsyncMock(return_value=mock_redis)):
            fetch_called = False

            async def fetch_fn():
                nonlocal fetch_called
                fetch_called = True
                return fresh_data

            value = await mgr.get_or_set(cache_key, ttl_seconds=300, fetch_fn=fetch_fn)
            assert value == fresh_data
            assert fetch_called is True
            mock_redis.get.assert_awaited_once_with(cache_key)
            mock_redis.setex.assert_awaited_once_with(
                cache_key, 300, json.dumps(fresh_data)
            )

        await mgr.close()

    @pytest.mark.asyncio
    async def test_cache_invalidation_by_pattern(self):
        """Pattern-based invalidation deletes all matching keys."""
        mgr = CacheManager(redis_url="redis://localhost:6379/0")

        # Simulate Redis SCAN returning keys then deleting them
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        # SCAN returns (cursor, [keys]) — first call returns keys, second ends
        mock_redis.scan = AsyncMock(
            side_effect=[
                (42, [b"patients:list:1", b"patients:list:2", b"patients:list:3"]),
                (0, [b"patients:list:4"]),
            ]
        )
        # delete is called once per SCAN batch; first batch deletes 3, second deletes 1
        mock_redis.delete = AsyncMock(side_effect=[3, 1])

        with patch.object(mgr, "_ensure_connection", AsyncMock(return_value=mock_redis)):
            deleted = await mgr.invalidate("patients:list:*")
            assert deleted == 4
            assert mock_redis.scan.await_count == 2
            assert mock_redis.delete.await_count == 2

        await mgr.close()

    @pytest.mark.asyncio
    async def test_cache_graceful_degradation_when_redis_unavailable(self):
        """When Redis is down, get_or_set falls through to fetch_fn without error."""
        mgr = CacheManager(redis_url="redis://localhost:6379/0")

        with patch.object(mgr, "_ensure_connection", AsyncMock(return_value=None)):
            async def fetch_fn():
                return {"fallback": "ok"}

            value = await mgr.get_or_set("any:key", ttl_seconds=60, fetch_fn=fetch_fn)
            assert value == {"fallback": "ok"}

            # Invalidation should return 0 (no-op)
            deleted = await mgr.invalidate("any:*")
            assert deleted == 0

        await mgr.close()

    @pytest.mark.asyncio
    async def test_cache_get_or_set_returns_none_without_fetch_fn(self):
        """When cache misses and no fetch_fn, returns None."""
        mgr = CacheManager(redis_url="redis://localhost:6379/0")

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)

        with patch.object(mgr, "_ensure_connection", AsyncMock(return_value=mock_redis)):
            value = await mgr.get_or_set("missing:key", ttl_seconds=60)
            assert value is None

        await mgr.close()


class TestCacheDecorator:
    """Verify the @cache_decorator for async functions."""

    @pytest.mark.asyncio
    async def test_decorator_caches_async_function_result(self):
        call_count = 0

        @cache_decorator(ttl_seconds=60)
        async def expensive_computation(x: int, y: int = 2) -> dict:
            nonlocal call_count
            call_count += 1
            return {"result": x * y}

        cached_value = {"result": 42}

        mgr = cache_manager
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        # First call: cache miss
        mock_redis.get = AsyncMock(side_effect=[None, json.dumps(cached_value)])
        mock_redis.setex = AsyncMock(return_value=True)

        with patch.object(mgr, "_ensure_connection", AsyncMock(return_value=mock_redis)):
            # First call: miss, compute, store
            result1 = await expensive_computation(6, y=7)
            assert result1 == {"result": 42}
            assert call_count == 1

            # Second call: hit, skip computation
            call_count_before = call_count
            result2 = await expensive_computation(6, y=7)
            assert result2 == cached_value
            assert call_count == call_count_before

        await mgr.close()
