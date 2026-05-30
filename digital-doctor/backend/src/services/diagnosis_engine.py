"""Assisted diagnosis engine — rule-based first pass + LLM second pass.

Implements a two-stage differential diagnosis pipeline:
  1. Rule engine matches patient data against T2DM classification rules
  2. For complex cases, LLM-based second pass with de-identified data

Confidence scoring weights rule-engine results (60%) and LLM analysis (40%).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from src.engine.rule_loader import RuleLoader
from src.engine.rule_engine import RuleEngine
from src.services.llm_client import llm_client
from src.services.diagnosis_prompts import (
    DIFFERENTIAL_DIAGNOSIS_SYSTEM,
    DIAGNOSIS_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

# Singleton — rule engine loaded once
_loader = RuleLoader()
_rules = _loader.load("t2dm_guidelines_v1")
_engine = RuleEngine(_rules)


def _build_rule_match_summary(matches: list[dict]) -> str:
    """Format rule-engine matches into a human-readable summary for the LLM prompt."""
    if not matches:
        return "规则引擎未匹配到明确的诊断规则。请基于临床数据独立分析。"

    lines = []
    for m in matches:
        lines.append(
            f"- [{m.get('id', '?')}] {m.get('name', '规则未命名')}: "
            f"{m.get('conclusion', '')} "
            f"(置信度: {m.get('confidence', 'unknown')}, "
            f"参考: {m.get('reference', 'N/A')})"
        )
    return "\n".join(lines)


def _format_lab_results(lab_results: dict | None) -> str:
    """Format lab results dict into readable text."""
    if not lab_results:
        return "无额外化验结果"
    lines = []
    for key, value in lab_results.items():
        if isinstance(value, dict):
            lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "无额外化验结果"


def _default_str(value: Any, default: str = "未知") -> str:
    """Return string representation of value, or default if None/empty."""
    if value is None:
        return default
    s = str(value)
    return s if s.strip() else default


def _build_prompt_user_message(
    patient_data: dict,
    pre_consult_summary: dict | None,
    lab_results: dict | None,
    rule_matches: list[dict],
) -> str:
    """Fill the diagnosis user template with patient data."""
    pc = pre_consult_summary or {}
    return DIAGNOSIS_USER_TEMPLATE.format(
        gender=_default_str(patient_data.get("gender"), "未知"),
        birth_year=_default_str(patient_data.get("birth_year"), "未知"),
        diabetes_type=_default_str(patient_data.get("diabetes_type"), "未知"),
        bmi=_default_str(patient_data.get("bmi"), "未知"),
        waist_circumference=_default_str(patient_data.get("waist_circumference"), "未知"),
        blood_pressure=_default_str(patient_data.get("blood_pressure"), "未知"),
        family_history="是" if patient_data.get("family_history") else "否" if "family_history" in patient_data else "未知",
        has_hypertension="是" if patient_data.get("has_hypertension") else "否" if "has_hypertension" in patient_data else "未知",
        physical_activity=_default_str(patient_data.get("physical_activity"), "未知"),
        fpg=_default_str(patient_data.get("fpg"), "未知"),
        ppg=_default_str(patient_data.get("ppg"), "未知"),
        hba1c=_default_str(patient_data.get("hba1c"), "未知"),
        tc=_default_str(patient_data.get("tc"), "未知"),
        tg=_default_str(patient_data.get("tg"), "未知"),
        ldl=_default_str(patient_data.get("ldl"), "未知"),
        hdl=_default_str(patient_data.get("hdl"), "未知"),
        egfr=_default_str(patient_data.get("egfr"), "未知"),
        pre_consult_summary=pc.get("summary", "无问诊摘要") if isinstance(pc, dict) else _default_str(pre_consult_summary, "无问诊摘要"),
        lab_results=_format_lab_results(lab_results),
        rule_matches=_build_rule_match_summary(rule_matches),
    )


def _parse_llm_json(response_text: str) -> dict:
    """Attempt to parse LLM response as JSON; return empty dict on failure."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response (may be wrapped in markdown)
        import re
        match = re.search(r"\{[\s\S]*\}", response_text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse LLM diagnosis response as JSON")
        return {}


def _is_complex_case(rule_matches: list[dict], patient_data: dict) -> bool:
    """Determine if a case needs LLM second pass.

    Complex cases include:
    - No rule matches (atypical presentation)
    - Low-confidence matches only
    - Multiple conflicting matches
    """
    if not rule_matches:
        return True

    diagnosis_matches = [m for m in rule_matches if m.get("category") == "diagnosis"]
    if not diagnosis_matches:
        return True

    # If any match has low confidence, flag as complex
    has_low = any(m.get("confidence") == "low" for m in diagnosis_matches)
    if has_low:
        return True

    # If there are multiple high-confidence matches that conflict, flag as complex
    high_conf = [m for m in diagnosis_matches if m.get("confidence") == "high"]
    if len(high_conf) >= 2:
        # Check if they point to different conclusions
        conclusions = {m.get("conclusion", "") for m in high_conf}
        if len(conclusions) >= 2:
            return True

    return False


def calculate_confidence(rule_matches: list[dict], llm_analysis: dict | None) -> float:
    """Calculate overall confidence score.

    Weights: rule-engine results (60%) + LLM analysis (40%).

    Rule confidence mapping:
      - high: 1.0, medium: 0.6, low: 0.3

    LLM confidence mapping (from llm_analysis["primary_diagnosis"]["confidence"]):
      - high: 1.0, medium: 0.6, low: 0.3

    Returns a float between 0.0 and 1.0.
    """
    # Rule-engine confidence (60% weight)
    if not rule_matches:
        rule_score = 0.0
    else:
        confidence_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
        diagnosis_matches = [m for m in rule_matches if m.get("category") == "diagnosis"]
        if diagnosis_matches:
            scores = [confidence_map.get(m.get("confidence", "low"), 0.3) for m in diagnosis_matches]
            rule_score = sum(scores) / len(scores)
        else:
            rule_score = 0.0

    # LLM confidence (40% weight)
    if llm_analysis and "primary_diagnosis" in llm_analysis:
        llm_conf = llm_analysis["primary_diagnosis"].get("confidence", "low")
        confidence_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
        llm_score = confidence_map.get(llm_conf, 0.3)
    else:
        llm_score = 0.0

    return round(0.6 * rule_score + 0.4 * llm_score, 2)


async def differential_diagnosis(
    patient_data: dict,
    pre_consult_summary: dict | None = None,
    lab_results: dict | None = None,
) -> dict:
    """Perform differential diagnosis combining rule engine and LLM analysis.

    Pipeline:
      1. Rule-based first pass against T2DM classification rules
      2. If complex case: LLM-based second pass with de-identified data
      3. Merge results and compute confidence

    Args:
        patient_data: Dict with keys like fpg, hba1c, bmi, age, egfr, etc.
        pre_consult_summary: Optional dict with "summary" and other ask-consult fields.
        lab_results: Optional dict of additional lab results.

    Returns:
        dict with keys:
          - primary_diagnosis: {type, subtype, confidence, guideline_ref}
          - differentials: [{condition, probability, supporting_evidence, ruling_out_needed}]
          - recommended_tests: [{test, urgency, rationale}]
          - overall_confidence: float (0.0-1.0)
          - method: "rule_only" | "rule_plus_llm"
    """
    # Stage 1: Rule-based first pass
    rule_matches = _engine.evaluate(patient_data, category="diagnosis")

    # Stage 2: LLM second pass for complex cases
    llm_analysis: dict | None = None
    method = "rule_only"

    if _is_complex_case(rule_matches, patient_data):
        method = "rule_plus_llm"
        try:
            # Sanitize patient data for LLM
            safe_data = llm_client.sanitize_clinical_data(patient_data)

            # Build prompt
            user_message = _build_prompt_user_message(
                safe_data, pre_consult_summary, lab_results, rule_matches
            )

            messages = [
                {"role": "system", "content": DIFFERENTIAL_DIAGNOSIS_SYSTEM},
                {"role": "user", "content": user_message},
            ]

            response_text = await llm_client.chat(messages, expect_json=True)
            llm_analysis = _parse_llm_json(response_text)
        except Exception as exc:
            logger.warning("LLM diagnosis analysis failed, falling back to rule-only: %s", exc)
            llm_analysis = None
            method = "rule_only"

    # Stage 3: Merge results
    overall_confidence = calculate_confidence(rule_matches, llm_analysis)

    # Build rule-based output
    result = _build_result_from_rules(patient_data, rule_matches, llm_analysis)
    result["overall_confidence"] = overall_confidence
    result["method"] = method

    return result


def _build_result_from_rules(
    patient_data: dict,
    rule_matches: list[dict],
    llm_analysis: dict | None,
) -> dict:
    """Build the structured diagnosis result from rule matches and optional LLM analysis."""
    diagnosis_matches = [m for m in rule_matches if m.get("category") == "diagnosis"]

    # If LLM provided structured analysis, use it as primary source
    if llm_analysis and "primary_diagnosis" in llm_analysis:
        primary = llm_analysis["primary_diagnosis"]
        differentials = llm_analysis.get("differentials", [])
        recommended_tests = llm_analysis.get("recommended_tests", [])
        narrative = llm_analysis.get("narrative", "")
    else:
        primary, differentials, recommended_tests, narrative = _derive_from_rules(
            patient_data, diagnosis_matches
        )

    return {
        "primary_diagnosis": primary,
        "differentials": differentials,
        "recommended_tests": recommended_tests,
        "narrative": narrative,
    }


def _derive_from_rules(
    patient_data: dict,
    diagnosis_matches: list[dict],
) -> tuple[dict, list[dict], list[dict], str]:
    """Derive diagnosis result purely from rule matches (no LLM)."""
    fpg = patient_data.get("fpg")
    hba1c = patient_data.get("hba1c")

    # Classify based on FPG and HbA1c thresholds
    primary = {
        "type": "未明确诊断",
        "subtype": None,
        "confidence": "low",
        "guideline_ref": "中国2型糖尿病防治指南(2024版) §4.1",
    }

    if fpg is not None and isinstance(fpg, (int, float)):
        if fpg >= 7.0:
            primary = {
                "type": "2型糖尿病",
                "subtype": None,
                "confidence": "high",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §4.1 (FPG ≥ 7.0 mmol/L)",
            }
        elif fpg >= 6.1:
            primary = {
                "type": "糖尿病前期",
                "subtype": "空腹血糖受损(IFG)",
                "confidence": "high",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §4.2 (6.1 ≤ FPG < 7.0)",
            }
        else:
            primary = {
                "type": "血糖正常",
                "subtype": None,
                "confidence": "medium",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §4.1",
            }

    if hba1c is not None and isinstance(hba1c, (int, float)) and hba1c >= 6.5:
        if primary["type"] == "糖尿病前期":
            primary = {
                "type": "2型糖尿病",
                "subtype": None,
                "confidence": "high",
                "guideline_ref": "中国2型糖尿病防治指南(2024版) §4.1 (HbA1c ≥ 6.5%)",
            }

    # Build differentials from matched rules
    differentials = []
    for m in diagnosis_matches:
        prob = "高" if m.get("confidence") == "high" else "中" if m.get("confidence") == "medium" else "低"
        differentials.append({
            "condition": m.get("name", "未知诊断"),
            "probability": prob,
            "supporting_evidence": m.get("conclusion", ""),
            "ruling_out_needed": "否" if m.get("confidence") == "high" else "是",
        })

    # If no differentials from rules, add default based on FPG
    if not differentials and fpg is not None:
        differentials = [
            {
                "condition": "正常血糖",
                "probability": "高" if fpg < 6.1 else "低",
                "supporting_evidence": f"FPG = {fpg} mmol/L",
                "ruling_out_needed": "否" if fpg < 6.1 else "是",
            }
        ]

    # Recommend tests based on findings
    recommended_tests: list[dict] = []
    if primary["type"] == "2型糖尿病" or primary["type"] == "糖尿病前期":
        recommended_tests.append({
            "test": "口服葡萄糖耐量试验(OGTT)",
            "urgency": "常规",
            "rationale": "确诊糖代谢状态的金标准检查",
        })
        recommended_tests.append({
            "test": "糖化血红蛋白(HbA1c)",
            "urgency": "常规",
            "rationale": "评估近3个月平均血糖水平",
        })
    if primary["type"] == "2型糖尿病":
        recommended_tests.extend([
            {
                "test": "尿微量白蛋白/肌酐比值(UACR)",
                "urgency": "常规",
                "rationale": "糖尿病肾病筛查",
            },
            {
                "test": "眼底检查",
                "urgency": "建议",
                "rationale": "糖尿病视网膜病变筛查",
            },
            {
                "test": "血脂全套",
                "urgency": "常规",
                "rationale": "评估心血管风险，糖尿病常伴血脂异常",
            },
        ])

    narrative = f"根据{primary['guideline_ref']}，患者当前诊断为{primary['type']}。"
    if primary["subtype"]:
        narrative += f"亚型为{primary['subtype']}。"

    return primary, differentials, recommended_tests, narrative
