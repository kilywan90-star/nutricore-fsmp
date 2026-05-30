"""Explanation data models — structured feature attribution for AI decisions.

Zero ML dependencies. Pure rule-based attribution using:
  1. Rule-engine matches → guideline references
  2. LLM structured JSON → cited factors
  3. Risk factor scores → clinical interpretation
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FactorContribution:
    """Single factor's contribution to a decision."""
    factor: str          # e.g. "空腹血糖", "eGFR", "age", "BMI"
    value: Any           # actual patient value
    threshold: str       # guideline threshold, e.g. "≥7.0 mmol/L"
    impact: str          # "positive" (supports), "negative" (rules out), "neutral"
    weight: float        # 0.0–1.0 contribution weight
    guideline_ref: str   # e.g. "中国2型糖尿病防治指南(2024版) §4.1"


@dataclass
class DiagnosisExplanation:
    """Full explanation for a differential diagnosis result."""
    primary_diagnosis: str
    confidence: float
    primary_factors: list[FactorContribution] = field(default_factory=list)
    rule_contributions: list[dict] = field(default_factory=list)
    differentials: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "primary_diagnosis": self.primary_diagnosis,
            "confidence": self.confidence,
            "primary_factors": [
                {
                    "factor": f.factor,
                    "value": f.value,
                    "threshold": f.threshold,
                    "impact": f.impact,
                    "weight": f.weight,
                    "guideline_ref": f.guideline_ref,
                }
                for f in self.primary_factors
            ],
            "rule_contributions": self.rule_contributions,
            "differentials": self.differentials,
            "summary": self.summary,
        }


@dataclass
class PrescriptionExplanation:
    """Explanation for a prescription review result."""
    overall_rating: str  # safe / caution / unsafe
    issues: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "overall_rating": self.overall_rating,
            "issues": self.issues,
            "summary": self.summary,
        }


@dataclass
class RiskExplanation:
    """Explanation for a risk assessment result."""
    risk_level: str
    contributing_factors: list[dict] = field(default_factory=list)
    modifiable_factors: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "risk_level": self.risk_level,
            "contributing_factors": self.contributing_factors,
            "modifiable_factors": self.modifiable_factors,
            "summary": self.summary,
        }
