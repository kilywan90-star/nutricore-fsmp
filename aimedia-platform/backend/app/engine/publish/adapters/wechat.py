"""微信公众号适配器（骨架）"""

from app.engine.publish.adapters.base import ChannelAdapter


class WechatMPAdapter(ChannelAdapter):
    """微信公众号"""

    async def publish(self, content: dict) -> dict:
        # TODO: 对接微信公众平台 API
        return {"id": "placeholder", "url": ""}

    async def retract(self, content_id: str) -> bool:
        return True

    async def get_status(self, content_id: str) -> dict:
        return {"status": "published"}

    def supported_formats(self) -> list[str]:
        return ["article"]

    def rate_limits(self) -> dict:
        return {"daily_max": 30, "qps": 1}
