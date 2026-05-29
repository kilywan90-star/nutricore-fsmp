"""
发布调度引擎 —— 定时/错峰/重试/一键撤回。
"""

import asyncio
from datetime import datetime
from enum import Enum
from uuid import UUID


class PublishStatus(str, Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PARTIAL_SUCCESS = "partial_success"
    SUCCESS = "success"
    FAILED = "failed"
    RETRACTED = "retracted"


class PublishScheduler:
    """发布调度器"""

    MAX_RETRIES = 3
    STAGGER_SECONDS = 300  # 多平台错峰间隔 5 分钟

    def __init__(self):
        self._adapters: dict[str, object] = {}

    def register_adapter(self, channel: str, adapter: object):
        self._adapters[channel] = adapter

    async def publish(self, content: dict, channels: list[str],
                      scheduled_at: datetime | None = None) -> dict:
        """执行发布任务"""
        if scheduled_at and scheduled_at > datetime.now():
            delay = (scheduled_at - datetime.now()).total_seconds()
            await asyncio.sleep(delay)

        results = {}
        for i, channel in enumerate(channels):
            if i > 0:
                await asyncio.sleep(self.STAGGER_SECONDS)

            adapter = self._adapters.get(channel)
            if adapter is None:
                results[channel] = {"status": "failed", "error": f"未找到渠道适配器: {channel}"}
                continue

            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    result = await adapter.publish(content)
                    results[channel] = {"status": "success", "external_id": result.get("id")}
                    break
                except Exception as e:
                    if attempt == self.MAX_RETRIES:
                        results[channel] = {"status": "failed", "error": str(e)}
                    else:
                        await asyncio.sleep(2 ** attempt)

        return self._summarize(results, channels)

    async def retract(self, content_id: UUID, channels: list[str]) -> dict:
        """一键撤回"""
        results = {}
        for channel in channels:
            adapter = self._adapters.get(channel)
            if adapter is None:
                continue
            try:
                await adapter.retract(str(content_id))
                results[channel] = "retracted"
            except Exception as e:
                results[channel] = f"failed: {e}"
        return results

    def _summarize(self, results: dict, channels: list[str]) -> dict:
        successes = sum(1 for r in results.values() if r["status"] == "success")
        failures = sum(1 for r in results.values() if r["status"] == "failed")

        if failures == 0:
            overall = PublishStatus.SUCCESS
        elif successes == 0:
            overall = PublishStatus.FAILED
        else:
            overall = PublishStatus.PARTIAL_SUCCESS

        return {"overall_status": overall.value, "channel_results": results}
