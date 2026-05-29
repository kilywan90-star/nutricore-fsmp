"""
隐私脱敏检测器 —— 扫描并标记患者个人信息。

覆盖《个人信息保护法》《负面行为清单》第3条。
"""

import re

from app.engine.compliance.engine import Finding


class PrivacyMasker:
    """隐私信息检测 + 脱敏"""

    PATTERNS = [
        ("PRV001", "身份证号", re.compile(r"\b\d{17}[\dXx]\b"), "critical",
         "《个人信息保护法》第28条：身份证号为敏感个人信息"),
        ("PRV002", "手机号", re.compile(r"\b1[3-9]\d{9}\b"), "high",
         "《个人信息保护法》第28条：手机号为敏感个人信息"),
        ("PRV003", "病历号", re.compile(r"(病历号|病案号|住院号|门诊号|就诊号)[:：]?\s*\d+"), "critical",
         "《负面行为清单》第3条：禁止泄露患者个人信息"),
        ("PRV004", "家庭住址", re.compile(
            r"((省|市|区|县|镇|乡|村|路|街|巷|栋|幢|单元|号|室).{0,30}){3,}"), "high",
         "《个人信息保护法》第28条"),
        ("PRV005", "银行卡号", re.compile(r"\b\d{16,19}\b"), "high",
         "《个人信息保护法》第28条"),
        ("PRV006", "姓名+病症", re.compile(
            r"([刘张李王陈杨赵黄周吴徐孙马胡朱郭何罗高林郑梁谢唐许冯宋韩邓彭曹曾田萧潘袁蔡蒋余于杜叶程魏苏吕丁任卢姚沈钟姜崔谭陆范汪廖石金贾韦夏付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤]"
            r"[^\s，。,!！?？]{1,3})"
            r"[\s，,]*[：:、]?"
            r"[\s]*((患|确诊|诊断|检测出|查出).{0,10}(病|症|癌|炎|瘤|栓|梗|溃疡|结节|囊肿|增生))"), "critical",
         "《负面行为清单》第3条 + 《个人信息保护法》：姓名+病症直接关联，属敏感信息"),
    ]

    def detect(self, text: str) -> list[Finding]:
        findings = []
        for rule_id, name, pattern, severity, law_ref in self.PATTERNS:
            for match in pattern.finditer(text):
                findings.append(Finding(
                    rule_id=rule_id,
                    severity=severity,
                    location=f"pos {match.start()}:{match.end()}",
                    message=f"[{name}] 发现疑似信息: 「{match.group()[:30]}...」",
                    law_ref=law_ref,
                ))
        return findings

    def mask(self, text: str) -> str:
        """对文本执行脱敏处理"""
        # 身份证
        text = re.sub(r"\b(\d{3})\d{11}(\d{3}[\dXx])\b", r"\1****\2", text)
        # 手机号
        text = re.sub(r"\b(1[3-9]\d)\d{4}(\d{4})\b", r"\1****\2", text)
        # 病历号
        text = re.sub(r"(病历号|病案号|住院号|门诊号|就诊号)[:：]?\s*\d+", r"\1[已脱敏]", text)
        # 银行卡
        text = re.sub(r"\b\d{4}\d{8,11}(\d{4})\b", r"****\1", text)
        return text
