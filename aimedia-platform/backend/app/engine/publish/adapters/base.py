"""渠道适配器基类"""

from abc import ABC, abstractmethod


class ChannelAdapter(ABC):
    """所有渠道适配器必须实现此接口"""

    @abstractmethod
    async def publish(self, content: dict) -> dict:
        """
        发布内容到渠道。
        返回: {"id": "external_content_id", "url": "..."}
        """

    @abstractmethod
    async def retract(self, content_id: str) -> bool:
        """撤回已发布内容"""

    @abstractmethod
    async def get_status(self, content_id: str) -> dict:
        """查询发布状态"""

    @abstractmethod
    def supported_formats(self) -> list[str]:
        """返回支持的格式: article/video/image/audio"""

    @abstractmethod
    def rate_limits(self) -> dict:
        """返回频率限制: {"daily_max": 100, "qps": 5}"""
