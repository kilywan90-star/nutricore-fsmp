"""
广告合规检测器 —— 基于规则的高速检测（<50ms）。

覆盖《医疗广告认定指南》六大红线 + 《负面行为清单》广告相关条款。
"""

import re

from app.engine.compliance.engine import Finding

# ── 广告合规规则库 ──

# 规则1: 疗效承诺词 → 红线第六条
GUARANTEE_WORDS = re.compile(
    r"(根治|包治|治愈|断根|除根|无风险|零风险|100%|百分百|保证|确保|肯定|绝对有效|永不复发|彻底康复)"
)

# 规则2: 主观评价词 → 红线第六条
SUPERLATIVE_WORDS = re.compile(
    r"(最好|最佳|第一|首个|唯一|最先进|最大|顶级|领先|独创|专利|国家级|国际级|最高级别)"
)

# 规则3: 对比表述 → 红线第六条第3款
COMPARISON_PATTERNS = re.compile(
    r"(比其他|优于|胜过|远超|大幅领先|别家|其他医院|别的医院)"
)

# 规则4: 促销/导流 → 红线第五条第3款 + 第八条第5款
PROMOTION_PATTERNS = re.compile(
    r"(免费|优惠|折扣|特价|团购|套餐价|限时|名额有限|扫码|加微信|咨询电话|预约挂号|点击购买|立即购买|马上预约)"
)

# 规则5: 病例推介模式 → 第八条第4款
CASE_PROMOTION = re.compile(
    r"(典型案例|成功案例|患者.*案例|康复案例|治疗案例|真实案例).{0,50}(医院|机构|就诊|治疗)"
)

# 规则6: 医疗广告禁止内容（《广告法》《医疗广告管理办法》）
BANNED_CONTENT = re.compile(
    r"(神医|神药|祖传秘方|偏方|特效药|一次根治|三天见效|七天痊愈)"
)

# 规则7: 隐含跳转意图 → 第八条第5款
REDIRECT_INTENT = re.compile(
    r"(点击.*了解更多|扫码.*咨询|添加.*微信|拨打.*电话|来院|到院|就诊.*优惠)"
)


class AdDetector:
    """广告合规规则检测器"""

    RULES = [
        ("AD001", "疗效承诺", GUARANTEE_WORDS, "critical",
         "《医疗广告认定指南》第六条：禁止对诊疗效果进行保证性承诺"),
        ("AD002", "主观夸大表述", SUPERLATIVE_WORDS, "high",
         "《医疗广告认定指南》第六条：禁止对医疗机构/服务做主观夸大表述"),
        ("AD003", "横向比较", COMPARISON_PATTERNS, "high",
         "《医疗广告认定指南》第六条第3款：禁止与其他医疗机构比较"),
        ("AD004", "促销导流", PROMOTION_PATTERNS, "critical",
         "《医疗广告认定指南》第八条第5款：科普页面附加跳转/购买链接构成广告"),
        ("AD005", "病例推介", CASE_PROMOTION, "critical",
         "《医疗广告认定指南》第八条第4款：以病例方式推介医疗机构构成广告"),
        ("AD006", "禁止性内容", BANNED_CONTENT, "critical",
         "《广告法》第十七条、《医疗广告管理办法》第七条：禁止神医神药等宣传"),
        ("AD007", "隐含导流意图", REDIRECT_INTENT, "high",
         "《医疗广告认定指南》第八条第5款：科普中隐含跳转意图可构成变相广告"),
    ]

    def detect(self, text: str) -> list[Finding]:
        findings = []
        for rule_id, name, pattern, severity, law_ref in self.RULES:
            for match in pattern.finditer(text):
                findings.append(Finding(
                    rule_id=rule_id,
                    severity=severity,
                    location=f"pos {match.start()}:{match.end()}",
                    message=f"[{name}] 命中「{match.group()}」",
                    law_ref=law_ref,
                ))
        return findings
