import time
from typing import List, Optional
from hashlib import md5

from agent_security_detector.core.context import DetectionResult, DetectionResponse, RiskLevel

class ResultAggregator:
    """结果聚合器，负责将多个插件的检测结果聚合为统一的响应"""

    def __init__(
        self,
        min_confidence: float = 0.5,
        duplicate_dedup: bool = True,
        risk_priority: List[RiskLevel] = None
    ):
        """
        初始化聚合器
        :param min_confidence: 最低置信度，低于此值的结果会被过滤
        :param duplicate_dedup: 是否去重重复的检测结果
        :param risk_priority: 风险等级优先级，用于确定最高风险等级
        """
        self.min_confidence = min_confidence
        self.duplicate_dedup = duplicate_dedup
        self.risk_priority = risk_priority or [
            RiskLevel.CRITICAL,
            RiskLevel.HIGH,
            RiskLevel.MEDIUM,
            RiskLevel.LOW
        ]

    def aggregate(
        self,
        results: List[DetectionResult],
        session_id: Optional[str] = None,
        processing_start_time: Optional[float] = None
    ) -> DetectionResponse:
        """
        聚合检测结果
        :param results: 检测结果列表
        :param session_id: 会话ID
        :param processing_start_time: 处理开始时间戳，用于计算处理时间
        :return: 聚合后的检测响应
        """
        start_time = processing_start_time or time.time()

        # 1. 过滤低置信度结果
        filtered_results = [
            r for r in results
            if r.confidence >= self.min_confidence
        ]

        # 2. 去重重复结果
        if self.duplicate_dedup:
            filtered_results = self._deduplicate_results(filtered_results)

        # 3. 计算最高风险等级
        highest_risk_level = self._get_highest_risk_level(filtered_results)

        # 4. 计算处理时间
        processing_time = (time.time() - start_time) * 1000  # 转换为毫秒

        # 5. 构造响应
        return DetectionResponse(
            session_id=session_id,
            has_risk=len(filtered_results) > 0,
            highest_risk_level=highest_risk_level,
            results=filtered_results,
            processing_time=processing_time
        )

    def _deduplicate_results(self, results: List[DetectionResult]) -> List[DetectionResult]:
        """
        去重重复的检测结果
        :param results: 检测结果列表
        :return: 去重后的结果列表
        """
        seen = set()
        unique_results = []

        for result in sorted(results, key=lambda x: x.confidence, reverse=True):
            # 生成结果的唯一标识
            result_key = self._generate_result_key(result)
            if result_key not in seen:
                seen.add(result_key)
                unique_results.append(result)

        return unique_results

    def _generate_result_key(self, result: DetectionResult) -> str:
        """
        生成检测结果的唯一标识，用于去重
        :param result: 检测结果
        :return: 唯一标识字符串
        """
        key_parts = [
            result.risk_type,
            result.description,
            str(result.details.get("position", "")),
            str(result.details.get("content", "")[:100])  # 取内容前100个字符
        ]
        key_str = "|".join(key_parts)
        return md5(key_str.encode("utf-8")).hexdigest()

    def _get_highest_risk_level(self, results: List[DetectionResult]) -> Optional[RiskLevel]:
        """
        获取最高风险等级
        :param results: 检测结果列表
        :return: 最高风险等级，如果没有风险返回None
        """
        if not results:
            return None

        for level in self.risk_priority:
            if any(r.risk_level == level for r in results):
                return level

        return None
```
