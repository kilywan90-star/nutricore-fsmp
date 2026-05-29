"""Tests for enhanced LLM client: mock responses, retry, circuit breaker."""
import json

import pytest
from httpx import HTTPStatusError

from src.services.llm_client import (
    LLMClient,
    CircuitBreaker,
    CircuitState,
    _validate_response,
    _estimate_message_tokens,
)


class TestMockResponses:
    """Verify fallback mock responses are well-formed."""

    @pytest.fixture
    def client(self):
        return LLMClient()

    def test_risk_assessment_mock(self, client):
        messages = [{"role": "user", "content": "请进行风险评估"}]
        reply = client._mock_response(messages)
        parsed = json.loads(reply)
        assert "risk_level" in parsed
        assert "score" in parsed
        assert "recommendations" in parsed

    def test_report_interpretation_mock(self, client):
        messages = [{"role": "user", "content": "请解读这份报告"}]
        reply = client._mock_response(messages)
        assert len(reply) > 0
        assert "血糖" in reply or "mmol" in reply

    def test_glucose_mock(self, client):
        messages = [{"role": "user", "content": "今天的血糖怎么样"}]
        reply = client._mock_response(messages)
        assert "血糖" in reply or "mmol" in reply

    def test_fallback_mock(self, client):
        messages = [{"role": "user", "content": "random query"}]
        reply = client._mock_response(messages)
        assert len(reply) > 0


class TestRetryLogic:
    """Verify retry with exponential backoff when LLM API fails transiently."""

    @pytest.fixture
    def client(self):
        return LLMClient()

    @pytest.mark.asyncio
    async def test_retries_and_eventually_succeeds(self, client, monkeypatch):
        """After 2 failures, the 3rd attempt succeeds."""
        call_count = 0
        original = client._make_request

        async def flaky_make_request(messages, temperature, expect_json):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Simulate a transient HTTP 503 error
                import httpx
                raise HTTPStatusError(
                    "Service Unavailable",
                    request=httpx.Request("POST", "http://test"),
                    response=httpx.Response(503),
                )
            return "最终成功的回复"

        monkeypatch.setattr(client, "_make_request", flaky_make_request)
        # Force the circuit to allow requests
        client._circuit = CircuitBreaker(failure_threshold=999)
        # Ensure API key is set so it doesn't fall back to mock
        monkeypatch.setattr(client, "api_key", "test-key")

        result = await client.chat([{"role": "user", "content": "测试"}])
        assert result == "最终成功的回复"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_retries_and_falls_back(self, client, monkeypatch):
        """When all retries fail, fall back to mock response."""
        async def always_fail(*args, **kwargs):
            import httpx
            raise HTTPStatusError(
                "Service Unavailable",
                request=httpx.Request("POST", "http://test"),
                response=httpx.Response(503),
            )

        monkeypatch.setattr(client, "_make_request", always_fail)
        monkeypatch.setattr(client, "api_key", "test-key")
        monkeypatch.setattr(client, "fallback_enabled", True)

        result = await client.chat([{"role": "user", "content": "血糖相关咨询"}])
        assert len(result) > 0


class TestCircuitBreaker:
    """Verify circuit breaker state machine."""

    def test_closed_allows_requests(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
        assert cb.allow_request() is True
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3
        assert cb.allow_request() is False

    def test_stays_open_before_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_half_opens_after_recovery_seconds(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=2, recovery_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Simulate time passing
        monkeypatch.setattr(cb, "last_failure_time", 0)
        # Override allow_request to simulate elapsed > recovery
        # We do this by patching time.monotonic in the method
        import time as _time
        original_monotonic = _time.monotonic
        _time.monotonic = lambda: 100.0  # Way past recovery window
        try:
            assert cb.allow_request() is True
            assert cb.state == CircuitState.HALF_OPEN
        finally:
            _time.monotonic = original_monotonic

    def test_success_resets_circuit(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_second_failure_in_half_open_reopens(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=2, recovery_seconds=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Force half-open
        cb.state = CircuitState.HALF_OPEN

        # Half-open request fails — should immediately re-open
        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestResponseValidation:
    """Verify response validation guards."""

    def test_rejects_empty_response(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_response("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_response("   \n\t  ")

    def test_accepts_valid_text(self):
        result = _validate_response("血糖正常，继续保持。")
        assert result == "血糖正常，继续保持。"

    def test_rejects_invalid_json(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            _validate_response("not json", expect_json=True)

    def test_accepts_valid_json(self):
        result = _validate_response('{"key": "value"}', expect_json=True)
        assert result == '{"key": "value"}'


class TestTokenCounting:
    """Verify token estimation."""

    def test_estimates_tokens_for_messages(self):
        messages = [
            {"role": "system", "content": "你是一位医生。"},
            {"role": "user", "content": "空腹血糖6.5正常吗？"},
        ]
        tokens = _estimate_message_tokens(messages)
        assert tokens > 0

    def test_handles_empty_messages(self):
        assert _estimate_message_tokens([]) == 0

    def test_handles_multimodal_content(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "血糖报告"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img"}},
                ],
            },
        ]
        tokens = _estimate_message_tokens(messages)
        assert tokens > 0
