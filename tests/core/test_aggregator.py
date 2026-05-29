from agent_security_detector.core.aggregator import ResultAggregator
from agent_security_detector.core.context import DetectionResult, RiskLevel

def test_aggregator_initialization():
    aggregator = ResultAggregator()
    assert aggregator.min_confidence == 0.5
    assert aggregator.duplicate_dedup is True

def test_result_aggregation():
    aggregator = ResultAggregator()
    results = [
        DetectionResult(
            plugin_name="plugin1",
            risk_level=RiskLevel.LOW,
            risk_type="test",
            description="测试1",
            confidence=0.8
        ),
        DetectionResult(
            plugin_name="plugin2",
            risk_level=RiskLevel.HIGH,
            risk_type="test",
            description="测试2",
            confidence=0.9
        ),
        DetectionResult(
            plugin_name="plugin3",
            risk_level=RiskLevel.MEDIUM,
            risk_type="other",
            description="测试3",
            confidence=0.3  # 低于阈值，应该被过滤
        )
    ]

    response = aggregator.aggregate(results, session_id="test_session")

    assert response.has_risk is True
    assert response.highest_risk_level == RiskLevel.HIGH
    assert len(response.results) == 2  # 过滤掉了置信度低的结果
    assert response.session_id == "test_session"
    assert response.processing_time > 0

def test_duplicate_deduplication():
    aggregator = ResultAggregator(duplicate_dedup=True)
    results = [
        DetectionResult(
            plugin_name="plugin1",
            risk_level=RiskLevel.LOW,
            risk_type="test",
            description="相同的风险",
            confidence=0.8,
            details={"position": "response"}
        ),
        DetectionResult(
            plugin_name="plugin2",
            risk_level=RiskLevel.LOW,
            risk_type="test",
            description="相同的风险",
            confidence=0.85,
            details={"position": "response"}
        )
    ]

    response = aggregator.aggregate(results)
    assert len(response.results) == 1  # 重复结果被合并
    assert response.results[0].confidence == 0.85  # 保留置信度高的
```
