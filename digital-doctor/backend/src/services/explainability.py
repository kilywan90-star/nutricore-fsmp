"""Explainability engine — rule-based feature attribution for AI decisions.

Provides post-hoc explanations mapping clinical decisions back to
patient features, guideline rules, and risk factor scores.

Zero ML dependencies. Uses three attribution sources:
  1. Rule-engine matches → direct guideline references
  2. LLM structured JSON → cited factors
  3. Risk factor scores → clinical interpretation mapping
"""

from __future__ import annotations

import logging
from typing import Any

from src.models.explanation import (
    DiagnosisExplanation,
    FactorContribution,
    PrescriptionExplanation,
    RiskExplanation,
)

logger = logging.getLogger(__name__)

# ── Guideline references per clinical domain ──────────────────────────────

_GLUCOSE_GUIDELINE = "中国2型糖尿病防治指南(2024版)"
_DRUG_GUIDELINE = "中国2型糖尿病防治指南(2024版) §6"
_RISK_GUIDELINE = "中国2型糖尿病防治指南(2024版) §9"

# ── Modifiable factor list ────────────────────────────────────────────────

_MODIFIABLE_FACTORS = {
    "bmi_score", "bmi", "waist_score", "waist_circumference",
    "activity_score", "physical_activity", "glucose_score",
    "fasting_glucose", "fpg", "hba1c", "hypertension_score",
    "blood_pressure", "smoking", "diet",
}

# ── Risk factor clinical interpretation table ─────────────────────────────

_RISK_FACTOR_LABELS: dict[str, str] = {
    "age_score": "年龄",
    "bmi_score": "BMI（体重指数）",
    "waist_score": "腰围",
    "family_score": "糖尿病家族史",
    "activity_score": "体力活动水平",
    "glucose_score": "空腹血糖",
    "hypertension_score": "高血压",
}

_RISK_FACTOR_THRESHOLDS: dict[str, str] = {
    "age_score": "年龄≥45岁风险递增",
    "bmi_score": "BMI≥24超重，BMI≥28肥胖",
    "waist_score": "男性腰围≥90cm，女性≥85cm",
    "family_score": "一级亲属糖尿病史",
    "activity_score": "每周中等强度运动<150分钟",
    "glucose_score": "空腹血糖≥5.6 mmol/L",
    "hypertension_score": "已确诊高血压",
}

_RISK_ACTIONABLE: dict[str, str] = {
    "bmi_score": "通过饮食控制和运动将BMI降至24以下",
    "waist_score": "通过有氧运动和核心训练减少腹围",
    "activity_score": "每周至少150分钟中等强度运动（快走、游泳、骑车）",
    "glucose_score": "控制碳水化合物摄入，定期监测空腹血糖",
    "hypertension_score": "限盐（<5g/天），规律服药控制血压",
}


class ExplainabilityEngine:
    """Provides feature-level attribution for AI decisions without ML dependencies."""

    # ── Diagnosis explanation ─────────────────────────────────────────────

    def explain_diagnosis(
        self,
        diagnosis_result: dict,
        patient_data: dict,
        rule_matches: list[dict],
    ) -> DiagnosisExplanation:
        """For each diagnosis/differential, explain WHY.

        Attribution sources:
          - Rule engine matches (60%): directly mapped to guideline rules
          - LLM analysis (40%): parsed from structured JSON response
        """
        primary = diagnosis_result.get("primary_diagnosis", {})
        primary_dx = primary.get("type", "未明确诊断")
        confidence = diagnosis_result.get("overall_confidence", 0.0)

        # Build primary factors from rule matches and patient data
        primary_factors = self._build_diagnosis_factors(
            patient_data, rule_matches, diagnosis_result
        )

        # Build rule contribution list
        rule_contributions = self._build_rule_contributions(rule_matches)

        # Build differential explanations
        differentials = self._build_differential_explanations(
            diagnosis_result.get("differentials", []), patient_data, rule_matches
        )

        # Compute confidence breakdown
        confidence_breakdown = self._compute_confidence_breakdown(
            rule_matches, diagnosis_result
        )
        rule_score = confidence_breakdown.get("rule_score", 0.0)
        llm_score = confidence_breakdown.get("llm_score")

        summary = generate_explanation_summary(primary_factors, primary_dx)

        return DiagnosisExplanation(
            primary_diagnosis=primary_dx,
            confidence=confidence,
            primary_factors=primary_factors,
            rule_contributions=rule_contributions,
            differentials=differentials,
            summary=summary,
        )

    # ── Prescription review explanation ───────────────────────────────────

    def explain_prescription_review(
        self,
        review_result: dict,
        patient_data: dict,
    ) -> PrescriptionExplanation:
        """For each issue found, explain which drug x patient factor caused it."""
        overall = review_result.get("overall_rating", "safe")
        issues = review_result.get("issues", [])

        explained_issues: list[dict] = []
        for issue in issues:
            contributing = self._map_issue_to_factors(issue, patient_data)
            explained = {
                **issue,
                "contributing_factors": contributing,
                "recommendation_rationale": self._build_issue_rationale(issue),
            }
            explained_issues.append(explained)

        summary = self._build_prescription_summary(overall, explained_issues)

        return PrescriptionExplanation(
            overall_rating=overall,
            issues=explained_issues,
            summary=summary,
        )

    # ── Risk assessment explanation ───────────────────────────────────────

    def explain_risk_assessment(
        self,
        risk_result: dict,
        factor_scores: dict,
    ) -> RiskExplanation:
        """Maps each risk factor score to clinical meaning with actionable interpretation."""
        risk_level = risk_result.get("risk_level", "未知")
        total_score = risk_result.get("score", 0)
        max_score = risk_result.get("max_score", 45)

        contributing: list[dict] = []
        modifiable: list[dict] = []

        # Sort factors by score descending
        sorted_factors = sorted(
            factor_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        for factor_key, score_val in sorted_factors:
            if score_val == 0:
                continue

            label = _RISK_FACTOR_LABELS.get(factor_key, factor_key)
            threshold = _RISK_FACTOR_THRESHOLDS.get(factor_key, "")
            is_modifiable = factor_key in _MODIFIABLE_FACTORS
            impact_pct = round(score_val / max_score * 100, 1)

            entry = {
                "factor": label,
                "factor_key": factor_key,
                "score": score_val,
                "impact_pct": impact_pct,
                "threshold": threshold,
                "guideline_ref": _RISK_GUIDELINE,
            }

            if is_modifiable:
                entry["actionable_advice"] = _RISK_ACTIONABLE.get(factor_key, "")
                modifiable.append(entry)

            contributing.append(entry)

        summary = self._build_risk_summary(risk_level, total_score, modifiable)

        return RiskExplanation(
            risk_level=risk_level,
            contributing_factors=contributing,
            modifiable_factors=modifiable,
            summary=summary,
        )

    # ── Private helpers — diagnosis ───────────────────────────────────────

    def _build_diagnosis_factors(
        self,
        patient_data: dict,
        rule_matches: list[dict],
        diagnosis_result: dict,
    ) -> list[FactorContribution]:
        """Map patient data + rule matches to factor contributions."""
        factors: list[FactorContribution] = []
        primary = diagnosis_result.get("primary_diagnosis", {})
        primary_type = primary.get("type", "")

        # FPG factor
        fpg = patient_data.get("fpg")
        if fpg is not None:
            factors.append(FactorContribution(
                factor="空腹血糖(FPG)",
                value=f"{fpg} mmol/L",
                threshold="≥7.0 mmol/L (糖尿病), 6.1–6.9 mmol/L (IFG)",
                impact="positive" if fpg >= 6.1 else "negative",
                weight=0.25,
                guideline_ref=f"{_GLUCOSE_GUIDELINE} §4.1",
            ))

        # HbA1c factor
        hba1c = patient_data.get("hba1c")
        if hba1c is not None:
            factors.append(FactorContribution(
                factor="糖化血红蛋白(HbA1c)",
                value=f"{hba1c}%",
                threshold="≥6.5% (糖尿病)",
                impact="positive" if hba1c >= 6.5 else "negative",
                weight=0.25,
                guideline_ref=f"{_GLUCOSE_GUIDELINE} §4.1",
            ))

        # BMI
        bmi = patient_data.get("bmi")
        if bmi is not None:
            bmi_val = float(bmi)
            factors.append(FactorContribution(
                factor="BMI（体重指数）",
                value=f"{bmi_val:.1f} kg/m²",
                threshold="≥24 超重，≥28 肥胖（T2DM危险因素）",
                impact="positive" if bmi_val >= 24 else "negative",
                weight=0.10,
                guideline_ref=f"{_GLUCOSE_GUIDELINE} §3.2",
            ))

        # eGFR
        egfr = patient_data.get("egfr")
        if egfr is not None:
            egfr_val = float(egfr)
            factors.append(FactorContribution(
                factor="eGFR（估算肾小球滤过率）",
                value=f"{egfr_val:.0f} mL/min/1.73m²",
                threshold="≥90 正常, 60–89 轻度降低, <60 CKD",
                impact="neutral",
                weight=0.10,
                guideline_ref=f"{_GLUCOSE_GUIDELINE} §8.3",
            ))

        # Age
        age = patient_data.get("age")
        if age is None:
            birth_year = patient_data.get("birth_year")
            if birth_year:
                age = 2026 - int(birth_year)
        if age is not None:
            age_val = int(age)
            factors.append(FactorContribution(
                factor="年龄",
                value=f"{age_val}岁",
                threshold="≥45岁（T2DM风险增加）",
                impact="positive" if age_val >= 45 else "negative",
                weight=0.10,
                guideline_ref=f"{_GLUCOSE_GUIDELINE} §3.1",
            ))

        # Family history
        if "family_history" in patient_data:
            fam = patient_data["family_history"]
            factors.append(FactorContribution(
                factor="糖尿病家族史",
                value="有" if fam else "无",
                threshold="一级亲属糖尿病史",
                impact="positive" if fam else "negative",
                weight=0.10,
                guideline_ref=f"{_GLUCOSE_GUIDELINE} §3.1",
            ))

        # Rule match contributions
        for m in rule_matches:
            if m.get("category") == "diagnosis":
                confidence = m.get("confidence", "low")
                conf_weight = {"high": 0.15, "medium": 0.10, "low": 0.05}.get(confidence, 0.05)
                factors.append(FactorContribution(
                    factor=f"指南规则: {m.get('name', m.get('id', 'unknown'))}",
                    value=m.get("conclusion", ""),
                    threshold=f"匹配条件: {m.get('conditions', [])}",
                    impact="positive",
                    weight=conf_weight,
                    guideline_ref=m.get("reference", _GLUCOSE_GUIDELINE),
                ))

        # Sort by weight descending
        factors.sort(key=lambda f: f.weight, reverse=True)
        return factors

    def _build_rule_contributions(
        self,
        rule_matches: list[dict],
    ) -> list[dict]:
        """Build structured rule contribution list."""
        contributions: list[dict] = []
        diagnosis_matches = [m for m in rule_matches if m.get("category") == "diagnosis"]

        for m in diagnosis_matches:
            contributions.append({
                "rule_id": m.get("id", "unknown"),
                "rule_name": m.get("name", "未知规则"),
                "matched": True,
                "weight": {"high": 0.6, "medium": 0.4, "low": 0.2}.get(
                    m.get("confidence", "low"), 0.2
                ),
                "guideline_ref": m.get("reference", _GLUCOSE_GUIDELINE),
            })

        # If no diagnosis matches, note unmatched
        if not contributions:
            contributions.append({
                "rule_id": "none",
                "rule_name": "未匹配到明确诊断规则",
                "matched": False,
                "weight": 0.0,
                "guideline_ref": "",
            })

        return contributions

    def _build_differential_explanations(
        self,
        differentials: list[dict],
        patient_data: dict,
        rule_matches: list[dict],
    ) -> list[dict]:
        """Annotate each differential with its factor contributions."""
        result: list[dict] = []
        for diff in differentials:
            condition = diff.get("condition", "")
            # Derive factors specific to this differential from rule matches
            matching_rules = [
                m for m in rule_matches
                if m.get("name", "") == condition or m.get("conclusion", "") == condition
            ]
            diff_factors: list[dict] = []
            if matching_rules:
                for mr in matching_rules:
                    diff_factors.append({
                        "factor": f"规则匹配: {mr.get('name', '')}",
                        "value": mr.get("conclusion", ""),
                        "impact": "positive",
                        "guideline_ref": mr.get("reference", _GLUCOSE_GUIDELINE),
                    })

            result.append({
                "condition": condition,
                "probability": diff.get("probability", "未知"),
                "supporting_evidence": diff.get("supporting_evidence", ""),
                "ruling_out_needed": diff.get("ruling_out_needed", "否"),
                "factor_contributions": diff_factors,
            })

        return result

    def _compute_confidence_breakdown(
        self,
        rule_matches: list[dict],
        diagnosis_result: dict,
    ) -> dict:
        """Break down confidence into rule_score and llm_score components."""
        confidence_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
        diagnosis_matches = [m for m in rule_matches if m.get("category") == "diagnosis"]

        if diagnosis_matches:
            scores = [
                confidence_map.get(m.get("confidence", "low"), 0.3)
                for m in diagnosis_matches
            ]
            rule_score = round(sum(scores) / len(scores), 2)
        else:
            rule_score = 0.0

        # LLM score derived from diagnosis result
        method = diagnosis_result.get("method", "rule_only")
        llm_score = None
        if method == "rule_plus_llm":
            # Estimate from overall confidence minus rule contribution
            raw_llm_score = (diagnosis_result.get("overall_confidence", 0.0) - 0.6 * rule_score) / 0.4
            llm_score = round(max(0.0, min(1.0, raw_llm_score)), 2)

        combined = diagnosis_result.get("overall_confidence", 0.0)

        return {
            "rule_score": rule_score,
            "llm_score": llm_score,
            "combined": combined,
        }

    # ── Private helpers — prescription ────────────────────────────────────

    def _map_issue_to_factors(
        self,
        issue: dict,
        patient_data: dict,
    ) -> list[dict]:
        """Map a prescription issue to the specific drug/patient factors that caused it."""
        factors: list[dict] = []
        category = issue.get("category", "")
        description = issue.get("description", "")

        if category == "guideline_concordance":
            hba1c = patient_data.get("hba1c") or patient_data.get("lab_results", {}).get("hba1c")
            egfr = patient_data.get("egfr") or patient_data.get("lab_results", {}).get("egfr")
            if hba1c is not None:
                factors.append({
                    "factor": "HbA1c",
                    "value": f"{hba1c}%",
                    "impact": "positive",
                    "explanation": "HbA1c水平是判断治疗强度的关键指标",
                })
            if egfr is not None:
                factors.append({
                    "factor": "eGFR",
                    "value": f"{egfr} mL/min/1.73m²",
                    "impact": "neutral",
                    "explanation": "肾功能影响药物选择和剂量",
                })

        elif category == "drug_interaction":
            # Parse drug pair from description: "drug_a + drug_b: mechanism"
            parts = description.split(":", 1)
            drug_pair = parts[0].strip() if parts else ""
            factors.append({
                "factor": "联合用药",
                "value": drug_pair,
                "impact": "positive",
                "explanation": "两种药物存在已知相互作用",
            })

        elif category == "renal_dosing":
            egfr = patient_data.get("egfr") or patient_data.get("lab_results", {}).get("egfr")
            if egfr is not None:
                factors.append({
                    "factor": "eGFR",
                    "value": f"{egfr} mL/min/1.73m²",
                    "impact": "positive",
                    "explanation": f"eGFR={egfr} mL/min/1.73m²，需要根据肾功能调整剂量",
                })

        elif category in ("hepatic_dosing", "contraindication"):
            alt = patient_data.get("alt") or patient_data.get("lab_results", {}).get("alt")
            if alt is not None:
                factors.append({
                    "factor": "ALT（肝功能）",
                    "value": f"{alt} U/L",
                    "impact": "positive",
                    "explanation": "肝功能异常影响药物代谢和安全性",
                })

        elif category == "allergy":
            factors.append({
                "factor": "过敏史",
                "value": patient_data.get("allergies", "未知"),
                "impact": "positive",
                "explanation": "患者过敏史与处方药物存在交叉反应",
            })

        elif category == "pregnancy_safety":
            factors.append({
                "factor": "妊娠状态",
                "value": patient_data.get("pregnancy_status", "未知"),
                "impact": "positive",
                "explanation": "妊娠状态影响用药安全性分类",
            })

        # Default: include all relevant patient factors
        if not factors:
            for key in ("conditions", "allergies", "pregnancy_status"):
                if key in patient_data and patient_data[key]:
                    factors.append({
                        "factor": key,
                        "value": str(patient_data[key]),
                        "impact": "neutral",
                        "explanation": f"患者{key}与处方审查结果相关",
                    })

        return factors

    def _build_issue_rationale(self, issue: dict) -> str:
        """Build a concise rationale for why this issue matters."""
        severity = issue.get("severity", "minor")
        category = issue.get("category", "unknown")

        rationales = {
            "guideline_concordance": {
                "contraindicated": "该药物组合存在绝对禁忌，可能造成严重不良事件",
                "major": "与指南推荐方案存在显著偏差，需重点关注",
                "moderate": "与指南推荐方案不完全一致，建议评估后调整",
                "minor": "与指南最佳实践存在细微差异",
            },
            "drug_interaction": {
                "contraindicated": "禁止联合使用，存在已知严重相互作用",
                "major": "严重相互作用，显著增加不良反应风险",
                "moderate": "需要监测和调整剂量的中度相互作用",
                "minor": "轻微相互作用，通常剂量调整即可管理",
            },
            "renal_dosing": {
                "major": "肾功能显著下降，必须调整剂量以避免药物蓄积",
                "moderate": "肾功能轻度异常，建议根据eGFR调整剂量",
                "minor": "肾功能正常范围内，无需调整",
            },
        }

        return rationales.get(category, {}).get(severity, "需要进一步评估")

    def _build_prescription_summary(
        self,
        overall: str,
        issues: list[dict],
    ) -> str:
        """Generate Chinese natural language summary for prescription review."""
        if not issues:
            return "处方审核通过：所有药物均为安全组合，符合临床指南推荐。"

        severity_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        for iss in issues:
            sev = iss.get("severity", "minor")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            cat = iss.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        lines: list[str] = []
        if overall == "safe":
            lines.append("处方综合评级：安全。")
        elif overall == "caution":
            lines.append("处方综合评级：需关注。")
        else:
            lines.append("处方综合评级：不安全。")

        if "contraindicated" in severity_counts:
            lines.append(
                f"发现{severity_counts['contraindicated']}项禁忌用药，必须修改处方。"
            )
        if "major" in severity_counts:
            lines.append(
                f"发现{severity_counts['major']}项严重问题，建议调整后重新审核。"
            )
        if "moderate" in severity_counts:
            lines.append(
                f"发现{severity_counts['moderate']}项注意事项，请结合临床判断。"
            )

        lines.append(f"共审查{len(issues)}条用药问题，涵盖{len(category_counts)}个审核维度。")
        return " ".join(lines)

    # ── Private helpers — risk assessment ─────────────────────────────────

    def _build_risk_summary(
        self,
        risk_level: str,
        total_score: int,
        modifiable: list[dict],
    ) -> str:
        """Generate Chinese natural language risk summary."""
        parts: list[str] = [f"糖尿病风险评估等级：{risk_level}（总分{total_score}/45）。"]

        if modifiable:
            mod_names = [m["factor"] for m in modifiable[:3]]
            parts.append(f"可改善因素：{'、'.join(mod_names)}。")

        if risk_level in ("高危", "极高危"):
            parts.append("建议近期到内分泌科就诊，行OGTT+糖化血红蛋白检查。")
        elif risk_level == "中危":
            parts.append("建议3个月后复查空腹血糖，并行OGTT筛查。")
        else:
            parts.append("风险较低，保持健康生活方式，每年体检关注血糖。")

        return "".join(parts)


# ── Summary generator ────────────────────────────────────────────────────


def generate_explanation_summary(
    factors: list[FactorContribution],
    decision: str,
) -> str:
    """Generates Chinese natural language explanation.

    Example output:
    "诊断为2型糖尿病，依据：空腹血糖8.2 mmol/L（≥7.0，符合诊断标准），
     HbA1c 7.5%（≥6.5%，确认诊断），BMI 28.0 kg/m²（≥28，肥胖为危险因素），
     年龄55岁（≥45，风险增加）。参考：中国2型糖尿病防治指南(2024版) §4.1。"
    """
    if not factors:
        return f"当前诊断为{decision}。未获取到足够的患者数据以生成详细分析依据。建议补充空腹血糖、HbA1c、BMI等关键指标。"

    positive_factors = [f for f in factors if f.impact == "positive"]
    negative_factors = [f for f in factors if f.impact == "negative"]
    neutral_factors = [f for f in factors if f.impact == "neutral"]

    parts: list[str] = [f"诊断为{decision}，依据："]

    factor_sentences: list[str] = []
    for i, f in enumerate(positive_factors):
        icon = chr(ord("①") + min(i, 9))  # ①②③...
        factor_sentences.append(
            f"{icon} {f.factor} {f.value}（{f.threshold}）"
        )

    if negative_factors:
        for f in negative_factors:
            factor_sentences.append(
                f"- {f.factor} {f.value}（不符合诊断阈值）"
            )

    if neutral_factors:
        for f in neutral_factors:
            factor_sentences.append(
                f"- {f.factor} {f.value}（临床参考）"
            )

    parts.append("；".join(factor_sentences))

    # Add guideline reference
    refs = set(f.guideline_ref for f in factors if f.guideline_ref)
    if refs:
        parts.append(f"。参考：{'；'.join(sorted(refs))}。")

    return "".join(parts)


# ── Singleton ────────────────────────────────────────────────────────────

explainability_engine = ExplainabilityEngine()
