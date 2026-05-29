"""
LLM Gateway —— 模型路由、降级切换、成本控制。

场景路由:
  - 复杂推理(结构化提取/分析/语义检测) → DeepSeek-V3
  - 简单分类(意图识别/标签) → 本地 Qwen3-8B (暂用 DeepSeek)
  - Embedding → BGE-M3 本地 (暂用 API)
"""

from dataclasses import dataclass, field
from enum import Enum

from app.llm.client import llm_client


class TaskType(str, Enum):
    COMPLEX = "complex"    # 复杂推理
    SIMPLE = "simple"      # 简单分类
    EMBED = "embed"        # 向量化


@dataclass
class LLMCallResult:
    content: str
    model_used: str
    tokens_used: int = 0
    cost_estimate: float = 0.0


class LLMGateway:
    """模型路由网关"""

    async def chat(self, prompt: str, task_type: TaskType = TaskType.COMPLEX,
                   max_tokens: int = None) -> LLMCallResult:
        model = self._route(task_type)
        response = llm_client.chat(prompt, model=model, max_tokens=max_tokens)
        return LLMCallResult(content=response, model_used=model)

    async def chat_json(self, prompt: str, task_type: TaskType = TaskType.COMPLEX) -> dict | list:
        model = self._route(task_type)
        return llm_client.chat_json(prompt, model=model)

    async def ad_intent_detect(self, text: str) -> list:
        """用 LLM 做广告意图语义检测"""
        prompt = _AD_DETECT_PROMPT.format(content=text[:3000])
        result = await self.chat_json(prompt, TaskType.COMPLEX)
        findings = []
        for item in result if isinstance(result, list) else result.get("findings", []):
            from app.engine.compliance.engine import Finding
            findings.append(Finding(
                rule_id="LLM001",
                severity=item.get("severity", "medium"),
                location=item.get("evidence", ""),
                message=item.get("reason", ""),
                law_ref=item.get("law_ref", ""),
            ))
        return findings

    def _route(self, task_type: TaskType) -> str:
        from app.config import settings
        return settings.llm_model  # 一期统一用配置的模型


llm_gateway = LLMGateway()


_AD_DETECT_PROMPT = """你是医疗广告合规审核专家。根据《医疗广告认定指南》，检测文本是否存在变相广告。

判断标准：
1. 是否宣称诊疗技术优势、硬件设备优势或诊疗效果
2. 是否明示或暗示在特定机构就医能获得更好安全性/疗效/价格优惠
3. 是否以病例或案例方式推介具体医疗机构
4. 是否在科普中附加跳转入口或购买链接
5. 是否使用"最好""第一""独家""领先"等主观夸大词汇

对于每条违规，给出 severity（critical/high/medium/low）、evidence（引用原文片段）、reason（判定理由）、law_ref（法规引用）。

输出 JSON 格式：
[{{"severity":"...", "evidence":"...", "reason":"...", "law_ref":"..."}}]

待检测文本：
{content}
"""
