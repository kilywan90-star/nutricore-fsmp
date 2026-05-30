"""Tests for system health checks — database, Redis, LLM, disk, aggregate."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.health_service import (
    CheckResult,
    check_database,
    check_redis,
    check_llm,
    check_disk_space,
    system_health,
)


class TestSystemHealth:
    """Verify aggregate health check with component mocking."""

    @pytest.mark.asyncio
    async def test_all_healthy(self):
        """When all checks pass, overall status is healthy."""
        mock_db = CheckResult(status="healthy", latency_ms=1.5, message="Database reachable")
        mock_redis = CheckResult(status="healthy", latency_ms=0.8, message="Redis reachable")
        mock_llm = CheckResult(status="healthy", latency_ms=45.2, message="LLM API reachable")
        mock_disk = CheckResult(status="healthy", message="Disk 50.0 GB free of 100.0 GB (50.0%)")

        with (
            patch("src.services.health_service.check_database", AsyncMock(return_value=mock_db)),
            patch("src.services.health_service.check_redis", AsyncMock(return_value=mock_redis)),
            patch("src.services.health_service.check_llm", AsyncMock(return_value=mock_llm)),
            patch("src.services.health_service.check_disk_space", MagicMock(return_value=mock_disk)),
        ):
            result = await system_health()

        assert result["status"] == "healthy"
        assert result["checks"]["database"]["status"] == "healthy"
        assert result["checks"]["redis"]["status"] == "healthy"
        assert result["checks"]["llm"]["status"] == "healthy"
        assert result["checks"]["disk"]["status"] == "healthy"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_database_unhealthy(self):
        """When database is unreachable, overall status is unhealthy."""
        mock_db = CheckResult(status="unhealthy", latency_ms=0, message="Database unreachable")
        mock_redis = CheckResult(status="healthy", latency_ms=0.5, message="Redis reachable")
        mock_llm = CheckResult(status="healthy", latency_ms=30.0, message="LLM API reachable")
        mock_disk = CheckResult(status="healthy", message="Disk 50.0 GB free of 100.0 GB (50.0%)")

        with (
            patch("src.services.health_service.check_database", AsyncMock(return_value=mock_db)),
            patch("src.services.health_service.check_redis", AsyncMock(return_value=mock_redis)),
            patch("src.services.health_service.check_llm", AsyncMock(return_value=mock_llm)),
            patch("src.services.health_service.check_disk_space", MagicMock(return_value=mock_disk)),
        ):
            result = await system_health()

        assert result["status"] == "unhealthy"
        assert result["checks"]["database"]["status"] == "unhealthy"
