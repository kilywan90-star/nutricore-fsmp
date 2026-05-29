from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

def test_detection_context_creation():
    context = DetectionContext(
        prompt="测试用户输入",
        response="测试智能体输出",
        tool_calls=[{"name": "test_tool", "parameters": {"arg": "value"}}],
        session_id="test_session_123",
        user_id="user_456"
    )

    assert context.prompt == "测试用户输入"
    assert context.response == "测试智能体输出"
    assert len(context.tool_calls) == 1
    assert context.session_id == "test_session_123"
    assert context.user_id == "user_456"
    assert context.timestamp is not None

def test_detection_result_creation():
    result = DetectionResult(
        plugin_name="test_plugin",
        risk_level=RiskLevel.HIGH,
        risk_type="test_risk",
        description="发现测试风险",
        confidence=0.95,
        details={"position": "response", "content": "风险内容"}
    )

    assert result.plugin_name == "test_plugin"
    assert result.risk_level == RiskLevel.HIGH
    assert result.risk_type == "test_risk"
    assert result.confidence == 0.95
    assert result.details["content"] == "风险内容"
```
