import re
from typing import List, Dict, Any, Optional

from agent_security_detector.plugins.base import BaseDetectionPlugin
from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

class PromptInjectionPlugin(BaseDetectionPlugin):
    """提示注入检测插件，检测用户输入中的提示注入和越狱尝试"""

    name = "prompt_injection"
    description = "检测用户输入中的提示注入攻击和越狱尝试"
    version = "1.0.0"
    author = "security team"
    severity = RiskLevel.HIGH

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 提示注入检测关键词
        self.injection_keywords = [
            "忽略之前的指令",
            "忽略上面的所有指令",
            "无视之前的规则",
            "忽略系统提示",
            "忘记之前的所有要求",
            "现在开始你需要",
            "从现在开始你是",
            "假装你是",
            "扮演",
            "不需要遵守",
            "不要遵守",
            "突破限制",
            "绕过安全",
        ]

        # 越狱尝试检测关键词
        self.jailbreak_keywords = [
            "越狱",
            "jailbreak",
            "突破限制",
            "绕过安全",
            "没有限制",
            "不受限制",
            "不需要遵守任何规则",
            "忽略安全规则",
            "禁用安全协议",
            "如何制作",
            "如何创建",
            "如何获取",
            "非法",
            "违法",
            "犯罪",
        ]

        # 正则表达式模式
        self.injection_patterns = [
            re.compile(r'^(忽略|无视|忘记).*(指令|规则|提示|要求)', re.IGNORECASE),
            re.compile(r'^(现在开始|从现在起|假装|扮演).*(你是|作为)', re.IGNORECASE),
            re.compile(r'(不需要|不要|不用).*遵守.*(规则|限制|安全)', re.IGNORECASE),
        ]

    def detect(self, context: DetectionContext) -> Optional[DetectionResult]:
        prompt = context.prompt.lower()
        findings = []

        # 检测提示注入关键词
        for keyword in self.injection_keywords:
            if keyword in prompt:
                findings.append({
                    "type": "prompt_injection",
                    "keyword": keyword
                })

        # 检测提示注入正则模式
        for pattern in self.injection_patterns:
            if pattern.search(prompt):
                findings.append({
                    "type": "prompt_injection",
                    "pattern": pattern.pattern
                })

        # 检测越狱尝试
        for keyword in self.jailbreak_keywords:
            if keyword in prompt:
                findings.append({
                    "type": "jailbreak_attempt",
                    "keyword": keyword
                })

        if findings:
            # 确定风险类型和等级
            risk_types = list(set(f["type"] for f in findings))
            risk_type = risk_types[0] if len(risk_types) == 1 else "multiple_adversarial_attack"

            return DetectionResult(
                plugin_name=self.name,
                risk_level=RiskLevel.HIGH,
                risk_type=risk_type,
                description=f"检测到对抗性输入：{', '.join(risk_types)}",
                confidence=0.8,
                details={
                    "findings": findings,
                    "count": len(findings)
                },
                suggestion="建议拦截该请求，或对输入进行进一步的安全校验"
            )

        return None
```
