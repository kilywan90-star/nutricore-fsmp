from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

class BaseDetectionPlugin(ABC):
    """检测插件基类，所有检测插件都需要继承此类"""

    # 插件元信息，子类必须重写
    name: str = ""
    description: str = ""
    version: str = ""
    author: str = ""
    severity: RiskLevel = RiskLevel.MEDIUM

    def __init__(self, config: Dict[str, Any]):
        """
        初始化插件
        :param config: 插件配置参数
        """
        self.config = config
        self.enabled = config.get("enabled", True)

    @abstractmethod
    def detect(self, context: DetectionContext) -> Optional[DetectionResult]:
        """
        执行检测逻辑
        :param context: 检测上下文
        :return: 检测结果，如果没有风险返回None
        """
        pass

    def get_config_schema(self) -> Dict[str, Any]:
        """
        返回插件的配置JSON Schema，用于配置校验和UI生成
        :return: JSON Schema字典
        """
        return {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "是否启用插件",
                    "default": True
                }
            },
            "required": []
        }

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        校验插件配置是否合法
        :param config: 待校验的配置
        :return: 配置是否合法
        """
        # 简单校验，子类可以重写实现更复杂的校验
        return True
```
