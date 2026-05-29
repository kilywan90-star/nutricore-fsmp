from agent_security_detector import SecurityDetector
from agent_security_detector.core.context import RiskLevel

def test_detector_initialization():
    detector = SecurityDetector()
    assert detector is not None
    assert detector.scheduler is not None
    assert detector.aggregator is not None

def test_basic_detection():
    detector = SecurityDetector(auto_load_builtin_plugins=False)

    # 测试正常情况
    result = detector.detect(
        prompt="你好",
        response="你好！有什么我可以帮助你的吗？",
        tool_calls=[]
    )

    assert result.has_risk is False
    assert len(result.results) == 0
```
