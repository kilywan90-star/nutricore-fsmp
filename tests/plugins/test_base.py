from agent_security_detector.plugins.base import BaseDetectionPlugin
from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

class TestPlugin(BaseDetectionPlugin):
    name = "test_plugin"
    description = "测试插件"
    version = "1.0.0"
    author = "test"
    severity = RiskLevel.MEDIUM

    def detect(self, context):
        return DetectionResult(
            plugin_name=self.name,
            risk_level=RiskLevel.LOW,
            risk_type="test",
            description="测试检测结果",
            confidence=1.0
        )

def test_plugin_initialization():
    config = {"enabled": True}
    plugin = TestPlugin(config)
    assert plugin.config == config
    assert plugin.name == "test_plugin"
    assert plugin.version == "1.0.0"

def test_plugin_detection():
    plugin = TestPlugin({})
    context = DetectionContext(prompt="test", response="test")
    result = plugin.detect(context)
    assert result.plugin_name == "test_plugin"
    assert result.risk_level == RiskLevel.LOW
```
