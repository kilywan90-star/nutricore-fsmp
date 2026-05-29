"""
Python SDK 使用示例
"""
from agent_security_detector import SecurityDetector, RiskLevel

def main():
    # 初始化检测器
    detector = SecurityDetector(
        config={
            "min_confidence": 0.6,  # 设置最低置信度
            "max_workers": 5
        },
        rule_dirs=["rules"]  # 加载自定义规则
    )

    print("=== 同步检测示例 ===")

    # 检测包含敏感信息的响应
    result = detector.detect(
        prompt="我的手机号是多少？",
        response="你的手机号是13812345678",
        tool_calls=[],
        session_id="test_session_001"
    )

    print(f"是否有风险: {result.has_risk}")
    print(f"最高风险等级: {result.highest_risk_level}")
    print(f"处理时间: {result.processing_time:.2f}ms")

    if result.results:
        print("\n检测到的风险:")
        for risk in result.results:
            print(f"- [{risk.risk_level}] {risk.risk_type}: {risk.description}")
            print(f"  置信度: {risk.confidence}")
            print(f"  建议: {risk.suggestion}")

    print("\n=== 异步检测示例 ===")

    import asyncio
    async def run_async_detection():
        result = await detector.detect_async(
            prompt="查询用户信息",
            response="查询成功",
            tool_calls=[{
                "name": "query_database",
                "parameters": {
                    "sql": "SELECT * FROM users WHERE id = '1' OR '1'='1'"
                }
            }]
        )

        print(f"是否有风险: {result.has_risk}")
        if result.results:
            for risk in result.results:
                print(f"- [{risk.risk_level}] {risk.risk_type}: {risk.description}")

    asyncio.run(run_async_detection())

    # 关闭检测器
    detector.shutdown()

if __name__ == "__main__":
    main()
```
