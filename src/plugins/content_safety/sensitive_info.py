import re
from typing import List, Dict, Any, Optional

from agent_security_detector.plugins.base import BaseDetectionPlugin
from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

class SensitiveInfoPlugin(BaseDetectionPlugin):
    """敏感信息检测插件"""

    name = "sensitive_info"
    description = "检测输出中的敏感信息（手机号、身份证、邮箱、银行卡号等）"
    version = "1.0.0"
    author = "security team"
    severity = RiskLevel.MEDIUM

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 正则表达式规则
        self.patterns = {
            "phone": re.compile(r'\b1[3-9]\d{9}\b'),
            "id_card": re.compile(r'\b[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "bank_card": re.compile(r'\b\d{16,19}\b'),
            "address": re.compile(r'([一-龥]{2,}(省|市|区|县|街道|镇|乡|村|路|街|巷|号|院|园|小区|大厦|公寓))'),
        }

        # 可以通过配置自定义规则
        custom_patterns = self.config.get("custom_patterns", {})
        for name, pattern in custom_patterns.items():
            self.patterns[name] = re.compile(pattern)

        # 要检测的敏感类型
        self.detect_types = self.config.get("detect_types", list(self.patterns.keys()))

    def detect(self, context: DetectionContext) -> Optional[DetectionResult]:
        content = context.response
        matches = []

        for detect_type in self.detect_types:
            if detect_type not in self.patterns:
                continue

            pattern = self.patterns[detect_type]
            type_matches = pattern.findall(content)

            for match in type_matches:
                if isinstance(match, tuple):
                    match = match[0]
                matches.append({
                    "type": detect_type,
                    "value": match,
                    "position": content.find(match)
                })

        if matches:
            return DetectionResult(
                plugin_name=self.name,
                risk_level=self.severity,
                risk_type="sensitive_information",
                description=f"检测到敏感信息：{', '.join([f'{m[\"type\"]}({m[\"value\"]})' for m in matches])}",
                confidence=0.9,
                details={
                    "matches": matches,
                    "count": len(matches)
                },
                suggestion="建议对敏感信息进行脱敏处理"
            )

        return None

    def get_config_schema(self) -> Dict[str, Any]:
        schema = super().get_config_schema()
        schema["properties"].update({
            "custom_patterns": {
                "type": "object",
                "description": "自定义正则表达式规则，key为规则名称，value为正则表达式",
                "default": {}
            },
            "detect_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要检测的敏感类型列表",
                "default": ["phone", "id_card", "email", "bank_card", "address"]
            }
        })
        return schema
```
