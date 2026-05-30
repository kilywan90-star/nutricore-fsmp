"""Medical record generator — LLM-powered SOAP note and discharge summary generation.

Follows the pattern from diagnosis_engine.py:
  1. Builds prompts from encounter data using templates
  2. Calls LLM via llm_client with sanitized data and expect_json=True
  3. Parses JSON response
  4. Falls back to template-based generation if LLM unavailable
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from src.services.llm_client import llm_client
from src.services.record_templates import (
    SOAP_SYSTEM,
    SOAP_USER_TEMPLATE,
    DISCHARGE_SYSTEM,
    DISCHARGE_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON parsing helper (same pattern as diagnosis_engine._parse_llm_json)
# ---------------------------------------------------------------------------

def _parse_llm_json(response_text: str) -> dict:
    """Attempt to parse LLM response as JSON; return empty dict on failure."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{[\s\S]*\}", response_text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse LLM record response as JSON")
        return {}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _default_str(value: Any, default: str = "无") -> str:
    """Return string representation of value, or default if None/empty."""
    if value is None:
        return default
    s = str(value)
    return s if s.strip() else default


def _format_lab_results(lab_results: dict | None) -> str:
    """Format lab results dict into readable Chinese text."""
    if not lab_results:
        return "无化验结果"
    lines = []
    for key, value in lab_results.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "无化验结果"


def _format_glucose_data(glucose_records: list | None) -> str:
    """Format glucose records into readable text."""
    if not glucose_records:
        return "无血糖记录"
    lines = []
    for r in glucose_records[-10:]:  # last 10 records
        if isinstance(r, dict):
            mt = r.get("measure_type", "")
            val = r.get("value_mmol_l", "")
            ts = r.get("recorded_at", "")
            lines.append(f"- {mt}: {val} mmol/L ({ts})")
        else:
            lines.append(f"- {r}")
    return "\n".join(lines) if lines else "无血糖记录"


def _format_medications(medications: list | None) -> str:
    """Format medication list into readable text."""
    if not medications:
        return "无当前用药"
    lines = []
    for m in medications:
        if isinstance(m, dict):
            name = m.get("drug_name", m.get("name", "?"))
            dose = m.get("dosage", m.get("dose", ""))
            freq = m.get("frequency", "")
            lines.append(f"- {name} {dose} {freq}".strip())
        else:
            lines.append(f"- {m}")
    return "\n".join(lines) if lines else "无当前用药"


# ---------------------------------------------------------------------------
# SOAP-to-markdown
# ---------------------------------------------------------------------------

def _soap_to_markdown(content: dict) -> str:
    """Convert structured SOAP content dict to markdown for preview/export."""
    sections = []
    labels = {
        "subjective": "S — 主观资料 (Subjective)",
        "objective": "O — 客观资料 (Objective)",
        "assessment": "A — 评估 (Assessment)",
        "plan": "P — 计划 (Plan)",
    }
    for key, label in labels.items():
        text = content.get(key, "")
        sections.append(f"### {label}\n\n{text}\n")
    return "\n".join(sections)


def _discharge_to_markdown(content: dict) -> str:
    """Convert structured discharge content to markdown."""
    sections = []
    labels = {
        "admission_summary": "## 入院情况",
        "hospital_course": "## 住院经过",
        "discharge_diagnosis": "## 出院诊断",
        "discharge_orders": "## 出院医嘱",
        "follow_up_plan": "## 随访计划",
    }
    for key, label in labels.items():
        text = content.get(key, "")
        sections.append(f"{label}\n\n{text}\n")
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Template-based fallback generation (no LLM required)
# ---------------------------------------------------------------------------

def _fallback_soap(encounter_data: dict) -> dict:
    """Generate a basic SOAP note from encounter data without LLM.

    Uses structured rules to construct each SOAP section.
    """
    pc = encounter_data.get("pre_consult_summary", {})
    if isinstance(pc, dict):
        chief = pc.get("chief_complaint", "")
        hpi = pc.get("present_illness", "")
        past = pc.get("past_history", "")
        family = pc.get("family_history", "")
        social = pc.get("social_history", "")
    else:
        chief = _default_str(pc)
        hpi = ""
        past = ""
        family = ""
        social = ""

    # Subjective
    subj_parts = []
    if chief:
        subj_parts.append(f"主诉：{chief}")
    if hpi:
        subj_parts.append(f"现病史：{hpi}")
    if past:
        subj_parts.append(f"既往史：{past}")
    if family:
        subj_parts.append(f"家族史：{family}")
    if social:
        subj_parts.append(f"社会史：{social}")
    subjective = "；".join(subj_parts) if subj_parts else "患者就诊，问诊信息待补充。"

    # Objective
    lab_results = encounter_data.get("lab_results", {})
    glucose_records = encounter_data.get("glucose_records", [])
    obj_parts = []
    if lab_results:
        for key, value in lab_results.items():
            obj_parts.append(f"{key}: {value}")
    if glucose_records:
        latest = glucose_records[0] if isinstance(glucose_records[0], dict) else None
        if latest:
            obj_parts.append(f"近期血糖: {latest.get('value_mmol_l', '')} mmol/L ({latest.get('measure_type', '')})")
    objective = "；".join(obj_parts) if obj_parts else "客观检查结果待补充。"

    # Assessment
    diag = encounter_data.get("diagnosis_info", {})
    if isinstance(diag, dict):
        primary = diag.get("primary_diagnosis", {})
        diag_text = primary.get("type", "") if isinstance(primary, dict) else _default_str(diag)
    else:
        diag_text = _default_str(diag)
    assessment = f"诊断：{diag_text}。基于《中国2型糖尿病防治指南(2024版)》诊断标准。"

    # Plan
    meds = encounter_data.get("medications", [])
    plan_parts = []
    if meds:
        plan_parts.append("用药方案见当前用药记录")
    plan_parts.append("建议定期监测空腹及餐后血糖")
    plan_parts.append("建议每3个月复查HbA1c")
    plan_parts.append("下次随访时间待定")
    plan = "；".join(plan_parts)

    return {
        "subjective": subjective,
        "objective": objective,
        "assessment": assessment,
        "plan": plan,
    }


def _fallback_discharge(admission_data: dict) -> dict:
    """Generate a basic discharge summary without LLM."""
    chief = _default_str(admission_data.get("chief_complaint"))
    ad_date = _default_str(admission_data.get("admission_date"), "未知")
    ad_diag = _default_str(admission_data.get("admission_diagnosis"), "待补充")

    return {
        "admission_summary": f"患者因{chief}于{ad_date}入院。入院诊断：{ad_diag}。",
        "hospital_course": _default_str(admission_data.get("hospital_course"), "住院期间病情平稳，治疗过程待补充。"),
        "discharge_diagnosis": _default_str(admission_data.get("admission_diagnosis"), "出院诊断待补充。"),
        "discharge_orders": "遵医嘱继续当前用药方案；定期监测血糖；保持健康生活方式。",
        "follow_up_plan": "出院后2周内分泌科门诊复查；每3个月复查HbA1c、血脂、肾功能；每年进行眼底及足部检查。",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_soap_note(encounter_data: dict) -> dict:
    """Generate a structured SOAP note from encounter data.

    Args:
        encounter_data: dict with keys:
            - pre_consult_summary (dict|str): structured pre-consult data
            - lab_results (dict): lab test results
            - glucose_records (list): glucose measurement records
            - diagnosis_info (dict|str): diagnosis assessment
            - medications (list): current medication list

    Returns:
        dict with keys: subjective, objective, assessment, plan, markdown
    """
    try:
        safe_data = llm_client.sanitize_clinical_data(encounter_data)

        pc = safe_data.get("pre_consult_summary", {})
        if isinstance(pc, dict):
            pre_consult_str = pc.get("summary", json.dumps(pc, ensure_ascii=False, default=str))
        else:
            pre_consult_str = _default_str(pc)

        user_message = SOAP_USER_TEMPLATE.format(
            pre_consult_summary=pre_consult_str,
            lab_results=_format_lab_results(safe_data.get("lab_results")),
            glucose_data=_format_glucose_data(safe_data.get("glucose_records")),
            diagnosis_info=_default_str(safe_data.get("diagnosis_info")),
            medications=_format_medications(safe_data.get("medications")),
        )

        messages = [
            {"role": "system", "content": SOAP_SYSTEM},
            {"role": "user", "content": user_message},
        ]

        response_text = await llm_client.chat(messages, expect_json=True)
        content = _parse_llm_json(response_text)

        if not content or "subjective" not in content:
            logger.warning("LLM returned incomplete SOAP; using fallback")
            content = _fallback_soap(encounter_data)
    except Exception as exc:
        logger.warning("LLM SOAP generation failed, using fallback: %s", exc)
        content = _fallback_soap(encounter_data)

    markdown = _soap_to_markdown(content)
    content["markdown"] = markdown
    return content


async def generate_discharge_summary(admission_data: dict) -> dict:
    """Generate a structured discharge summary from admission data.

    Args:
        admission_data: dict with keys:
            - admission_date (str)
            - chief_complaint (str)
            - admission_diagnosis (str)
            - hospital_course (str)
            - lab_results (dict)
            - treatment_plan (str)
            - discharge_status (str)

    Returns:
        dict with keys: admission_summary, hospital_course, discharge_diagnosis,
                       discharge_orders, follow_up_plan, markdown
    """
    try:
        safe_data = llm_client.sanitize_clinical_data(admission_data)

        user_message = DISCHARGE_USER_TEMPLATE.format(
            admission_date=_default_str(safe_data.get("admission_date")),
            chief_complaint=_default_str(safe_data.get("chief_complaint")),
            admission_diagnosis=_default_str(safe_data.get("admission_diagnosis")),
            hospital_course=_default_str(safe_data.get("hospital_course")),
            lab_results=_format_lab_results(safe_data.get("lab_results")),
            treatment_plan=_default_str(safe_data.get("treatment_plan")),
            discharge_status=_default_str(safe_data.get("discharge_status")),
        )

        messages = [
            {"role": "system", "content": DISCHARGE_SYSTEM},
            {"role": "user", "content": user_message},
        ]

        response_text = await llm_client.chat(messages, expect_json=True)
        content = _parse_llm_json(response_text)

        if not content or "discharge_diagnosis" not in content:
            logger.warning("LLM returned incomplete discharge summary; using fallback")
            content = _fallback_discharge(admission_data)
    except Exception as exc:
        logger.warning("LLM discharge summary generation failed, using fallback: %s", exc)
        content = _fallback_discharge(admission_data)

    markdown = _discharge_to_markdown(content)
    content["markdown"] = markdown
    return content
