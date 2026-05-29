from agent_security_detector.plugins.tool_call_safety.injection_detection import InjectionDetectionPlugin
from agent_security_detector.core.context import DetectionContext, RiskLevel

def test_sql_injection_detection():
    plugin = InjectionDetectionPlugin({})

    # 测试SQL注入
    context = DetectionContext(
        prompt="test",
        response="查询结果",
        tool_calls=[{
            "name": "query_database",
            "parameters": {
                "sql": "SELECT * FROM users WHERE id = '1' OR '1'='1'"
            }
        }]
    )
    result = plugin.detect(context)
    assert result is not None
    assert result.risk_type == "sql_injection"
    assert result.risk_level == RiskLevel.HIGH
    assert "SQL注入" in result.description

def test_command_injection_detection():
    plugin = InjectionDetectionPlugin({})

    # 测试命令注入
    context = DetectionContext(
        prompt="test",
        response="执行结果",
        tool_calls=[{
            "name": "execute_command",
            "parameters": {
                "command": "rm -rf / || echo hello"
            }
        }]
    )
    result = plugin.detect(context)
    assert result is not None
    assert result.risk_type == "command_injection"
    assert result.risk_level == RiskLevel.CRITICAL
    assert "命令注入" in result.description

def test_safe_tool_call():
    plugin = InjectionDetectionPlugin({})

    # 测试安全的工具调用
    context = DetectionContext(
        prompt="test",
        response="正常结果",
        tool_calls=[{
            "name": "get_user_info",
            "parameters": {
                "user_id": 123
            }
        }]
    )
    result = plugin.detect(context)
    assert result is None
```
