"""Enhanced LLM client with retry, circuit breaker, token counting, and sanitizer integration."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from enum import Enum
from typing import AsyncGenerator

from httpx import AsyncClient, HTTPStatusError, RequestError, TimeoutException

from src.config import settings
from src.security.llm_sanitizer import sanitize_for_llm
from src.security.deidentifier import deidentify_clinical_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token counting — tiktoken if available, else character-based estimate
# ---------------------------------------------------------------------------

try:
    import tiktoken

    _TIKTOKEN_ENC = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(text: str) -> int:
        return len(_TIKTOKEN_ENC.encode(text))

except ImportError:
    # Fallback: ~4 chars per token for CJK text, ~4 chars per token for English
    def _count_tokens(text: str) -> int:
        return max(1, len(text) // 4)


def _estimate_message_tokens(messages: list[dict]) -> int:
    """Estimate total token count across all messages."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += _count_tokens(content)
        elif isinstance(content, list):
            # Multi-modal content
            total += sum(
                _count_tokens(part.get("text", ""))
                if isinstance(part, dict) and part.get("type") == "text"
                else 0
                for part in content
            )
    return total


def _validate_response(text: str | None, expect_json: bool = False) -> str:
    """Validate LLM response is well-formed and non-empty.

    Returns the text unchanged if valid; raises ValueError if not.
    """
    if not text or not text.strip():
        raise ValueError("LLM returned empty response")
    if expect_json:
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
    return text


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Simple circuit breaker: opens after *threshold* consecutive failures,
    stays open for *recovery_seconds*, then half-opens to test recovery."""

    def __init__(self, failure_threshold: int = 5, recovery_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.state == CircuitState.HALF_OPEN:
            # In HALF_OPEN, a single failure re-opens the circuit immediately.
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker re-OPENED after HALF_OPEN probe failure")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN after %d consecutive failures",
                self.failure_count,
            )

    def record_success(self) -> None:
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = CircuitState.CLOSED

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.recovery_seconds:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker HALF_OPEN — testing recovery")
                return True
            return False
        # HALF_OPEN — allow one probe request
        return True


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------


class LLMClient:
    """OpenAI-compatible LLM client.

    Works with OpenAI, DeepSeek, Qwen, GLM, and other compatible APIs.
    Includes automatic retry, circuit breaker, token counting, response
    validation, and mandatory input sanitization.
    """

    def __init__(self):
        self.base_url: str = settings.LLM_BASE_URL.rstrip("/")
        self.api_key: str = settings.LLM_API_KEY
        self.model: str = settings.LLM_MODEL
        self.max_tokens: int = settings.LLM_MAX_TOKENS
        self.default_temperature: float = settings.LLM_TEMPERATURE
        self.retry_count: int = settings.LLM_RETRY_COUNT
        self.timeout_seconds: int = settings.LLM_TIMEOUT_SECONDS
        self.fallback_enabled: bool = settings.LLM_FALLBACK_ENABLED
        self._circuit = CircuitBreaker()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        expect_json: bool = False,
    ) -> str:
        """Send a chat completion request with retry, circuit breaker, and sanitization.

        Each message's content is run through text-level de-identification
        before transmission.  Callers should also pre-sanitize any
        structured clinical data via ``sanitize_clinical_data()``.

        Returns the assistant's text response.
        """
        temp = temperature if temperature is not None else self.default_temperature
        sanitized_messages = self._sanitize_messages(messages)
        input_tokens = _estimate_message_tokens(sanitized_messages)

        if not self._circuit.allow_request():
            logger.warning("Circuit breaker open — falling back to mock")
            if self.fallback_enabled:
                return self._mock_response(messages)
            raise RuntimeError("LLM circuit breaker is OPEN and fallback is disabled")

        if not self.api_key:
            if self.fallback_enabled:
                return self._mock_response(messages)
            raise RuntimeError("LLM API key not configured and fallback is disabled")

        last_error: Exception | None = None
        for attempt in range(self.retry_count + 1):
            try:
                response_text = await self._make_request(
                    sanitized_messages, temp, expect_json
                )
                self._circuit.record_success()
                return response_text
            except (RequestError, HTTPStatusError, TimeoutException, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "LLM request attempt %d/%d failed: %s",
                    attempt + 1,
                    self.retry_count + 1,
                    exc,
                )
                if attempt < self.retry_count:
                    delay = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(delay)
                else:
                    self._circuit.record_failure()

        # All retries exhausted
        logger.error("LLM request failed after %d attempts", self.retry_count + 1)
        if self.fallback_enabled:
            return self._mock_response(messages)
        raise RuntimeError(f"LLM request failed: {last_error}") from last_error

    async def chat_stream(
        self,
        messages: list[dict],
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content chunks as they arrive."""
        temp = temperature if temperature is not None else self.default_temperature
        sanitized_messages = self._sanitize_messages(messages)

        if not self._circuit.allow_request():
            logger.warning("Circuit breaker open during streaming request")
            fallback = self._mock_response(messages) if self.fallback_enabled else ""
            yield fallback
            return

        if not self.api_key:
            if self.fallback_enabled:
                yield self._mock_response(messages)
                return
            raise RuntimeError("LLM API key not configured")

        start = time.monotonic()
        try:
            async with AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": sanitized_messages,
                        "temperature": temp,
                        "max_tokens": self.max_tokens,
                        "stream": True,
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = (
                                    chunk.get("choices", [{}])[0]
                                    .get("delta", {})
                                    .get("content", "")
                                )
                                if delta:
                                    yield delta
                            except json.JSONDecodeError:
                                continue
            self._circuit.record_success()
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.info("LLM streaming response | model=%s latency_ms=%.0f", self.model, elapsed_ms)
        except Exception as exc:
            self._circuit.record_failure()
            logger.error("LLM streaming request failed: %s", exc)
            if self.fallback_enabled:
                yield self._mock_response(messages)

    @staticmethod
    def sanitize_clinical_data(clinical_data: dict) -> dict:
        """Sanitize structured clinical data for LLM consumption.

        Call this before building prompts from clinical records.
        Returns a dict with only whitelisted safe fields plus audit metadata.
        """
        return sanitize_for_llm(clinical_data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _make_request(
        self,
        messages: list[dict],
        temperature: float,
        expect_json: bool,
    ) -> str:
        start = time.monotonic()
        async with AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": self.max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            elapsed_ms = (time.monotonic() - start) * 1000

            content = data["choices"][0]["message"]["content"]
            output_tokens = _count_tokens(content)

            usage = data.get("usage", {})
            logger.info(
                "LLM request | model=%s latency_ms=%.0f "
                "input_tokens_est=%d output_tokens=%d "
                "api_prompt_tokens=%s api_completion_tokens=%s",
                self.model,
                elapsed_ms,
                _estimate_message_tokens(messages),
                output_tokens,
                usage.get("prompt_tokens", "N/A"),
                usage.get("completion_tokens", "N/A"),
            )

            return _validate_response(content, expect_json=expect_json)

    def _sanitize_messages(self, messages: list[dict]) -> list[dict]:
        """Apply text-level de-identification to every message's content."""
        sanitized = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                content = deidentify_clinical_text(content)
            sanitized.append({**msg, "content": content})
        return sanitized

    def _mock_response(self, messages: list[dict]) -> str:
        """Rule-based fallback when LLM is unavailable."""
        last_msg = messages[-1]["content"] if messages else ""
        if "风险评估" in last_msg:
            return (
                '{"risk_level": "中危", "score": 12, '
                '"recommendations": ["建议生活方式干预", "3个月后复查空腹血糖"]}'
            )
        if "报告" in last_msg:
            return (
                "根据检查结果：空腹血糖 6.5mmol/L（轻度升高），"
                "HbA1c 7.2%（提示近3月血糖控制欠佳），"
                "总胆固醇 5.2mmol/L（正常）。"
                "建议：控制饮食碳水化合物摄入，增加有氧运动，"
                "遵医嘱服药，2周后复查空腹血糖。"
            )
        if "血糖" in last_msg:
            return (
                "您今日空腹血糖6.5mmol/L，在可接受范围。"
                "注意今日早餐碳水摄入量，保持午餐后散步15分钟。"
            )
        return "分析结果：无异常。"


llm_client = LLMClient()
