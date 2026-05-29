"""
DeepSeek V4 API 客户端封装
支持流式输出、超时重试、并发控制、token统计
"""
import asyncio
import os
import time
import logging
from typing import AsyncGenerator, Optional
from dataclasses import dataclass, field
from collections import deque

import httpx

logger = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost=self.cost + other.cost,
        )


@dataclass
class LLMConfig:
    api_key: str = field(default_factory=lambda: _env("DEEPSEEK_API_KEY", ""))
    api_base: str = field(default_factory=lambda: _env("DEEPSEEK_API_BASE", "https://api.deepseek.com"))
    model: str = field(default_factory=lambda: _env("DEEPSEEK_MODEL", "deepseek-chat"))
    max_tokens: int = 8192
    temperature: float = 0.3
    top_p: float = 0.9
    timeout: float = 120.0
    max_retries: int = 3
    retry_delay: float = 2.0
    max_concurrent: int = 5

    # Token 定价 (RMB per 1M tokens)
    input_price: float = 2.0
    output_price: float = 8.0


class RateLimiter:
    """滑动窗口并发控制"""

    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._window: deque = deque()
        self._window_size = 60  # 1 minute window
        self._max_per_window = max_concurrent * 10

    async def acquire(self):
        now = time.time()
        while self._window and now - self._window[0] > self._window_size:
            self._window.popleft()
        if len(self._window) >= self._max_per_window:
            wait_time = self._window[0] + self._window_size - now + 0.1
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        await self._semaphore.acquire()
        self._window.append(time.time())

    def release(self):
        self._semaphore.release()


class DeepSeekClient:
    """DeepSeek V4 API 客户端"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(self.config.max_concurrent)
        self._usage_log: list[TokenUsage] = []

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _calc_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens * self.config.input_price
            + completion_tokens * self.config.output_price
        ) / 1_000_000

    # ── 非流式调用 ──────────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict:
        """同步（非流式）调用，返回完整结果"""
        await self._rate_limiter.acquire()
        try:
            payload = self._build_payload(messages, system, temperature, max_tokens, stream=False)
            result = await self._request_with_retry(payload)
            self._log_usage(payload, result)
            return result
        finally:
            self._rate_limiter.release()

    # ── 流式调用 (SSE) ──────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """流式调用，yield 每个 delta chunk"""
        await self._rate_limiter.acquire()
        try:
            payload = self._build_payload(messages, system, temperature, max_tokens, stream=True)
            client = await self._get_client()

            last_error = None
            for attempt in range(self.config.max_retries + 1):
                try:
                    async with client.stream("POST", "/v1/chat/completions", json=payload) as resp:
                        if resp.status_code != 200:
                            body = await resp.aread()
                            raise RuntimeError(f"API error {resp.status_code}: {body.decode()}")

                        collected = []
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                import json
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    collected.append(content)
                                    yield content
                            elif line.strip() == "":
                                continue

                        # 记录 token 用量（从最后一个 chunk 获取）
                        try:
                            usage = chunk.get("usage", {})
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens", 0)
                                completion_tokens = usage.get("completion_tokens", 0)
                                self._record_usage(prompt_tokens, completion_tokens)
                        except Exception:
                            pass

                        return  # 成功，退出重试循环

                except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.RemoteProtocolError) as e:
                    last_error = e
                    if attempt < self.config.max_retries:
                        delay = self.config.retry_delay * (2**attempt)
                        logger.warning(f"Stream attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        raise RuntimeError(f"Stream failed after {self.config.max_retries + 1} attempts: {last_error}")

        finally:
            self._rate_limiter.release()

    # ── 内部方法 ────────────────────────────────────

    def _build_payload(
        self,
        messages: list[dict],
        system: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        stream: bool,
    ) -> dict:
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        return {
            "model": self.config.model,
            "messages": full_messages,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": stream,
        }

    async def _request_with_retry(self, payload: dict) -> dict:
        client = await self._get_client()
        last_error = None
        for attempt in range(self.config.max_retries + 1):
            try:
                resp = await client.post("/v1/chat/completions", json=payload)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", self.config.retry_delay))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2**attempt))
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2**attempt))
                else:
                    raise
        raise RuntimeError(f"Request failed after {self.config.max_retries + 1} attempts: {last_error}")

    def _record_usage(self, prompt_tokens: int, completion_tokens: int):
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost=self._calc_cost(prompt_tokens, completion_tokens),
        )
        self._usage_log.append(usage)

    def _log_usage(self, payload: dict, result: dict):
        usage = result.get("usage", {})
        self._record_usage(
            prompt_tokens=usage.get("prompt_tokens", len(payload.get("messages", [])) * 100),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    def get_total_usage(self) -> TokenUsage:
        total = TokenUsage()
        for u in self._usage_log:
            total = total + u
        return total

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# ── 全局客户端（按需初始化） ──────────────────────

_global_client: Optional[DeepSeekClient] = None


def get_client(config: Optional[LLMConfig] = None) -> DeepSeekClient:
    global _global_client
    if config:
        _global_client = DeepSeekClient(config)
    elif _global_client is None:
        _global_client = DeepSeekClient()
    return _global_client
