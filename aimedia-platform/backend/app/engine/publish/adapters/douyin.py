"""抖音健康适配器（骨架）"""

from app.engine.publish.adapters.base import ChannelAdapter


class DouyinAdapter(ChannelAdapter):
    """抖音"""

    async def publish(self, content: dict) -> dict:
        # TODO: 对接抖音开放平台 API
        return {"id": "placeholder", "url": ""}

    async def retract(self, content_id: str) -> bool:
        return True

    async def get_status(self, content_id: str) -> dict:
        return {"status": "published"}

    def supported_formats(self) -> list[str]:
        return ["video", "image"]

    def rate_limits(self) -> dict:
        return {"daily_max": 10, "qps": 1}
