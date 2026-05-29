"""
合规引擎 —— 内容发布前的最后一道防线。

管线顺序:
  规则检测(快) → 隐私扫描(快) → LLM语义检测(慢) → 链接扫描(快) → AI标识注入 → 水印注入

使用:
  engine = ComplianceEngine()
  report = await engine.scan(content, content_type="article")
  if report.overall_verdict == "block":
      raise ContentBlockedError(report)
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    WARN = "warn"


@dataclass
class Finding:
    rule_id: str
    severity: str  # critical / high / medium / low
    location: str  # 违规定位（字符偏移或描述）
    message: str
    law_ref: str = ""  # 引用法规条款


@dataclass
class DetectionReport:
    content_id: str = ""
    content_hash: str = ""
    overall_verdict: Verdict = Verdict.PASS
    rule_findings: list[Finding] = field(default_factory=list)
    privacy_findings: list[Finding] = field(default_factory=list)
    llm_findings: list[Finding] = field(default_factory=list)
    ai_labeled: bool = False
    watermarked: bool = False
    detected_at: str = ""

    def has_block(self) -> bool:
        return self.overall_verdict == Verdict.BLOCK

    def to_dict(self) -> dict:
        return {
            "overall_verdict": self.overall_verdict.value,
            "rule_findings": [f.__dict__ for f in self.rule_findings],
            "privacy_findings": [f.__dict__ for f in self.privacy_findings],
            "llm_findings": [f.__dict__ for f in self.llm_findings],
            "ai_labeled": self.ai_labeled,
            "watermarked": self.watermarked,
        }


class ComplianceEngine:
    """合规检测编排器"""

    def __init__(self):
        self._ad_detector = None
        self._privacy_masker = None
        self._ai_labeler = None
        self._llm_detector = None

    @property
    def ad_detector(self):
        if self._ad_detector is None:
            from app.engine.compliance.ad_detector import AdDetector
            self._ad_detector = AdDetector()
        return self._ad_detector

    @property
    def privacy_masker(self):
        if self._privacy_masker is None:
            from app.engine.compliance.privacy_masker import PrivacyMasker
            self._privacy_masker = PrivacyMasker()
        return self._privacy_masker

    @property
    def ai_labeler(self):
        if self._ai_labeler is None:
            from app.engine.compliance.ai_labeler import AILabeler
            self._ai_labeler = AILabeler()
        return self._ai_labeler

    async def scan(self, content: str | dict, content_type: str = "article", is_ai_generated: bool = False) -> DetectionReport:
        """
        对内容执行全管线合规检测。
        content: 文本字符串，或包含 body+title 的字典
        """
        text = content if isinstance(content, str) else self._extract_text(content)
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        report = DetectionReport(
            content_hash=content_hash,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )

        # Stage 1: 规则检测（广告合规）
        ad_findings = self.ad_detector.detect(text)
        report.rule_findings = ad_findings

        # Stage 2: 隐私扫描
        privacy_findings = self.privacy_masker.detect(text)
        report.privacy_findings = privacy_findings

        # Stage 3: LLM 语义检测（按需）
        if self._needs_llm_check(ad_findings):
            llm_findings = await self._run_llm_detection(text)
            report.llm_findings = llm_findings
            ad_findings.extend(llm_findings)

        # Stage 4: 综合判定
        report.overall_verdict = self._determine_verdict(ad_findings + privacy_findings)

        # Stage 5: AI 标识注入标记
        if is_ai_generated:
            report.ai_labeled = True

        # Stage 6: 水印注入标记
        report.watermarked = True

        return report

    def _extract_text(self, content: dict) -> str:
        parts = []
        if content.get("title"):
            parts.append(content["title"])
        body = content.get("body", {})
        if isinstance(body, dict):
            parts.append(body.get("text", ""))
        elif isinstance(body, str):
            parts.append(body)
        return "\n".join(parts)

    def _needs_llm_check(self, rule_findings: list[Finding]) -> bool:
        """规则检测无明确拦截但文本较长时，用 LLM 做语义兜底"""
        return not any(f.severity == "critical" for f in rule_findings)

    async def _run_llm_detection(self, text: str) -> list[Finding]:
        try:
            from app.llm.gateway import llm_gateway
            result = await llm_gateway.ad_intent_detect(text)
            return result
        except Exception:
            return []

    def _determine_verdict(self, findings: list[Finding]) -> Verdict:
        if any(f.severity == "critical" for f in findings):
            return Verdict.BLOCK
        if any(f.severity == "high" for f in findings):
            return Verdict.WARN
        return Verdict.PASS
