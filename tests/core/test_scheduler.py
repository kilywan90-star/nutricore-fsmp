import asyncio
from agent_security_detector.core.scheduler import PluginScheduler
from agent_security_detector.plugins.base import BaseDetectionPlugin
from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

class Plugin1(BaseDetectionPlugin):
    name = "plugin1"
    description = "测试插件1"
    version = "1.0.0"
    author = "test"

    def detect(self, context):
        return DetectionResult(
            plugin_name=self.name,
            risk_level=RiskLevel.LOW,
            risk_type="test1",
            description="测试结果1",
            confidence=0.9
        )

class Plugin2(BaseDetectionPlugin):
    name = "plugin2"
    description = "测试插件2"
    version = "1.0.0"
    author = "test"

    def detect(self, context):
        return DetectionResult(
            plugin_name=self.name,
            risk_level=RiskLevel.HIGH,
            risk_type="test2",
            description="测试结果2",
            confidence=0.95
        )

def test_scheduler_initialization():
    scheduler = PluginScheduler()
    assert len(scheduler.plugins) == 0

def test_plugin_registration():
    scheduler = PluginScheduler()
    plugin1 = Plugin1({})
    plugin2 = Plugin2({})

    scheduler.register_plugin(plugin1)
    scheduler.register_plugin(plugin2)

    assert len(scheduler.plugins) == 2
    assert "plugin1" in scheduler.plugins
    assert "plugin2" in scheduler.plugins

def test_sync_detection():
    scheduler = PluginScheduler()
    scheduler.register_plugin(Plugin1({}))
    scheduler.register_plugin(Plugin2({}))

    context = DetectionContext(prompt="test", response="test")
    results = scheduler.run_sync(context)

    assert len(results) == 2
    risk_types = [r.risk_type for r in results]
    assert "test1" in risk_types
    assert "test2" in risk_types

@pytest.mark.asyncio
async def test_async_detection():
    scheduler = PluginScheduler()
    scheduler.register_plugin(Plugin1({}))
    scheduler.register_plugin(Plugin2({}))

    context = DetectionContext(prompt="test", response="test")
    results = await scheduler.run_async(context)

    assert len(results) == 2
    risk_types = [r.risk_type for r in results]
    assert "test1" in risk_types
    assert "test2" in risk_types
```
