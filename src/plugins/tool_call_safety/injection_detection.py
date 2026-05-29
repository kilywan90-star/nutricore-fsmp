import re
from typing import List, Dict, Any, Optional

from agent_security_detector.plugins.base import BaseDetectionPlugin
from agent_security_detector.core.context import DetectionContext, DetectionResult, RiskLevel

class InjectionDetectionPlugin(BaseDetectionPlugin):
    """注入攻击检测插件，检测工具调用中的SQL注入、命令注入等攻击"""

    name = "injection_detection"
    description = "检测工具调用中的注入攻击（SQL注入、命令注入、代码注入等）"
    version = "1.0.0"
    author = "security team"
    severity = RiskLevel.HIGH

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # SQL注入检测规则
        self.sql_patterns = [
            re.compile(r'\b(OR|AND)\b\s+\d+\s*=\s*\d+', re.IGNORECASE),
            re.compile(r'\b(UNION|SELECT|INSERT|DELETE|UPDATE|DROP|ALTER|CREATE)\b', re.IGNORECASE),
            re.compile(r'--\s', re.IGNORECASE),
            re.compile(r';\s', re.IGNORECASE),
            re.compile(r"'", re.IGNORECASE),
            re.compile(r'"', re.IGNORECASE),
        ]

        # 命令注入检测规则
        self.command_patterns = [
            re.compile(r'[;&|`$]'),
            re.compile(r'\b(rm|del|format|mkfs)\b', re.IGNORECASE),
            re.compile(r'\b(chmod|chown|sudo|su)\b', re.IGNORECASE),
            re.compile(r'\b(wget|curl|nc|bash|sh|cmd|powershell)\b', re.IGNORECASE),
        ]

        # 代码注入检测规则
        self.code_patterns = [
            re.compile(r'\b(eval|exec|system|passthru|shell_exec)\b', re.IGNORECASE),
            re.compile(r'<\?php', re.IGNORECASE),
            re.compile(r'<script', re.IGNORECASE),
        ]

    def detect(self, context: DetectionContext) -> Optional[DetectionResult]:
        if not context.tool_calls:
            return None

        all_findings = []

        for tool_call in context.tool_calls:
            tool_name = tool_call.get("name", "")
            parameters = tool_call.get("parameters", {})

            # 检查所有参数值
            for param_name, param_value in parameters.items():
                if isinstance(param_value, str):
                    # 检测SQL注入
                    sql_findings = self._check_sql_injection(param_value)
                    if sql_findings:
                        all_findings.extend([{
                            "type": "sql_injection",
                            "tool_name": tool_name,
                            "param_name": param_name,
                            "value": param_value,
                            "pattern": pattern.pattern
                        } for pattern in sql_findings])

                    # 检测命令注入
                    command_findings = self._check_command_injection(param_value)
                    if command_findings:
                        all_findings.extend([{
                            "type": "command_injection",
                            "tool_name": tool_name,
                            "param_name": param_name,
                            "value": param_value,
                            "pattern": pattern.pattern
                        } for pattern in command_findings])

                    # 检测代码注入
                    code_findings = self._check_code_injection(param_value)
                    if code_findings:
                        all_findings.extend([{
                            "type": "code_injection",
                            "tool_name": tool_name,
                            "param_name": param_name,
                            "value": param_value,
                            "pattern": pattern.pattern
                        } for pattern in code_findings])

        if all_findings:
            # 确定最高风险等级
            highest_risk = RiskLevel.MEDIUM
            for finding in all_findings:
                if finding["type"] == "command_injection":
                    highest_risk = RiskLevel.CRITICAL
                    break
                elif finding["type"] == "sql_injection":
                    highest_risk = RiskLevel.HIGH

            return DetectionResult(
                plugin_name=self.name,
                risk_level=highest_risk,
                risk_type=all_findings[0]["type"],
                description=f"检测到注入攻击：{', '.join([f['type'] for f in all_findings])}",
                confidence=0.85,
                details={
                    "findings": all_findings,
                    "count": len(all_findings)
                },
                suggestion="建议对工具调用参数进行严格的输入校验和过滤"
            )

        return None

    def _check_sql_injection(self, value: str) -> List[re.Pattern]:
        """检查是否包含SQL注入特征"""
        findings = []
        for pattern in self.sql_patterns:
            if pattern.search(value):
                findings.append(pattern)
        return findings

    def _check_command_injection(self, value: str) -> List[re.Pattern]:
        """检查是否包含命令注入特征"""
        findings = []
        for pattern in self.command_patterns:
            if pattern.search(value):
                findings.append(pattern)
        return findings

    def _check_code_injection(self, value: str) -> List[re.Pattern]:
        """检查是否包含代码注入特征"""
        findings = []
        for pattern in self.code_patterns:
            if pattern.search(value):
                findings.append(pattern)
        return findings
```
