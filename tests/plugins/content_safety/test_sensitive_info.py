from agent_security_detector.plugins.content_safety.sensitive_info import SensitiveInfoPlugin
from agent_security_detector.core.context import DetectionContext, RiskLevel

def test_sensitive_info_detection():
    plugin = SensitiveInfoPlugin({})

    # 测试手机号检测
    context = DetectionContext(
        prompt="test",
        response="我的手机号是13812345678",
        tool_calls=[]
    )
    result = plugin.detect(context)
    assert result is not None
    assert result.risk_type == "sensitive_information"
    assert result.risk_level == RiskLevel.MEDIUM
    assert "手机号" in result.description
    assert result.details["matches"][0]["type"] == "phone"
    assert result.details["matches"][0]["value"] == "13812345678"

    # 测试身份证号检测
    context = DetectionContext(
        prompt="test",
        response="身份证号是110101199001011234",
        tool_calls=[]
    )
    result = plugin.detect(context)
    assert result is not None
    assert "身份证" in result.description
    assert result.details["matches"][0]["type"] == "id_card"

    # 测试邮箱检测
    context = DetectionContext(
        prompt="test",
        response="我的邮箱是test@example.com",
        tool_calls=[]
    )
    result = plugin.detect(context)
    assert result is not None
    assert "邮箱" in result.description
    assert result.details["matches"][0]["type"] == "email"

    # 测试正常内容
    context = DetectionContext(
        prompt="test",
        response="这是一段正常的内容，不包含敏感信息",
        tool_calls=[]
    )
    result = plugin.detect(context)
    assert result is None
```
