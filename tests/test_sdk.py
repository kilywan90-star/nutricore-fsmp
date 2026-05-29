from agent_security_detector import SecurityDetector

def test_sdk_basic_usage():
    """测试SDK基本使用"""
    detector = SecurityDetector()

    # 测试正常情况
    result = detector.detect(
        prompt="你好",
        response="你好！有什么可以帮助你的吗？",
        tool_calls=[]
    )
    assert result.has_risk is False

    # 测试敏感信息检测
    result = detector.detect(
        prompt="test",
        response="手机号：13912345678",
        tool_calls=[]
    )
    assert result.has_risk is True
    assert any(r.risk_type == "sensitive_information" for r in result.results)

    detector.shutdown()

@pytest.mark.asyncio
async def test_sdk_async_usage():
    """测试SDK异步接口"""
    detector = SecurityDetector()

    result = await detector.detect_async(
        prompt="test",
        response="邮箱：test@example.com",
        tool_calls=[]
    )

    assert result.has_risk is True
    assert any(r.risk_type == "sensitive_information" for r in result.results)

    detector.shutdown()
```
