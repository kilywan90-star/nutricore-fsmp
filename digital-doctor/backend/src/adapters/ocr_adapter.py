"""L3 OCR Adapter — extracts structured lab values from unstructured Chinese text.

For hospitals that can only export PDF/Excel reports. Uses pure regex — no ML needed.
Handles common OCR errors and both simplified/traditional Chinese characters.
"""

import re
from typing import Any


# ── OCR error correction map (common Chinese OCR mistakes) ──────────────────
OCR_FIX_MAP: dict[str, str] = {
    # Character-level errors
    "皿": "糖",      # 皿 → 糖
    "压": "血",      # 压 → 血 (in 血糖 context)
    "糗": "糖",      # 糠 → 糖
    # Unit-level errors
    "mmo1/L": "mmol/L",
    "mmoI/L": "mmol/L",
    "mm0l/L": "mmol/L",
    "umo1/L": "umol/L",
    "umoI/L": "umol/L",
    "g/I": "g/L",
    "g/1": "g/L",
    "mg/dI": "mg/dL",
    "mg/d1": "mg/dL",
    # Number OCR errors
    ". .": ".",
}

# Traditional-to-simplified mapping for common medical terms
TRAD_TO_SIMP: dict[str, str] = {
    "血糖": "血糖",   # 血糖 → 血糖 (same in both)
    "體檢": "体检",   # 體檢 → 体检
    "檢查": "检查",   # 檢查 → 检查
    "牙糖": "血糖",   # no trad for 血糖, but keep mapping
    "參考": "参考",   # 參考 → 参考
    "範圍": "范围",   # 範圍 → 范围
    "結果": "结果",   # 結果 → 结果
    "尿素": "尿素",   # 尿素 → 尿素 (same)
    "肌酐": "肌酐",   # 肌酐 → 肌酐 (same)
    "胆固醇": "胆固醇",  # 膽固醇 → 胆固醇
}

# Lab item name patterns (simplified Chinese, with traditional variants)
LAB_PATTERNS: dict[str, list[str]] = {
    "fpg": [
        r"(?:空腹)?血糖(?:[\(（]GLU[\)）])?",
        r"FPG",
        r"GLU(?:\s*\(空腹\))?",
        r"空腹.*血糖",
    ],
    "hba1c": [
        r"(?:糖化血红蛋白|糖化血紅蛋白)[\(（]?(?:HbA1c|HbA1C)[\)）]?",
        r"HbA1c",
        r"HbA1C",
        r"糖化(?:血红蛋白|血紅蛋白)",
    ],
    "tc": [
        r"(?:总|總)(?:胆固醇|膽固醇)[\(（]?(?:TC|CHO)[\)）]?",
        r"TC",
        r"CHO[LI]?",
        r"(?:血清)?总(?:胆固醇|膽固醇)",
    ],
    "ldl": [
        r"(?:低密度脂蛋白|低密度脂蛋白)[\(（]?(?:LDL|LDL-C)[\)）]?",
        r"LDL(?:-C)?",
        r"低密度(?:脂蛋白)?(?:胆固醇|膽固醇)?",
    ],
    "hdl": [
        r"(?:高密度脂蛋白|高密度脂蛋白)[\(（]?(?:HDL|HDL-C)[\)）]?",
        r"HDL(?:-C)?",
        r"高密度(?:脂蛋白)?(?:胆固醇|膽固醇)?",
    ],
    "tg": [
        r"(?:甘油三酯|三酸甘油酯)[\(（]?(?:TG|TRIG)[\)）]?",
        r"TG",
        r"TRIG",
        r"(?:血清)?甘油三酯",
    ],
    "creatinine": [
        r"(?:血)?(?:肌酐|肌酸酐)[\(（]?(?:Cr|CRE)[\)）]?",
        r"Cr(?:ea)?",
        r"CRE",
    ],
    "bun": [
        r"(?:尿素|尿素氮)[\(（]?(?:BUN|UREA)[\)）]?",
        r"BUN",
        r"UREA",
        r"(?:血)?尿素(?:氮)?",
    ],
    "uacr": [
        r"(?:尿微量白蛋白[\/／]肌酐(?:比值|比))",
        r"UACR",
        r"ACR",
    ],
    "egfr": [
        r"eGFR",
        r"(?:估算|估计)(?:肾小球滤过率|腎小球濾過率)",
        r"(?:估算)?GFR",
    ],
}


def _apply_ocr_fixes(text: str) -> str:
    """Apply common OCR error corrections to text."""
    for wrong, correct in OCR_FIX_MAP.items():
        text = text.replace(wrong, correct)
    return text


def _normalize_chinese(text: str) -> str:
    """Convert traditional Chinese characters to simplified for known medical terms."""
    for trad, simp in TRAD_TO_SIMP.items():
        text = text.replace(trad, simp)
    return text


def _extract_number(text: str) -> float | None:
    """Extract a numeric value from text, handling common OCR errors.

    Prefers standalone numbers (preceded by whitespace/punctuation) over
    numbers embedded in identifiers like HbA1c or GLU2.
    """
    # Try standalone numbers first — preceded by whitespace, parens, or start
    for match in re.finditer(r"(?:^|[\s(（,，])(\d+\.?\d*)", text):
        try:
            return float(match.group(1))
        except ValueError:
            continue

    # Fall back to any number
    match = re.search(r"(\d+\.?\d*)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _find_reference_range(text: str) -> tuple[str | None, str | None, str | None]:
    """Extract reference range from text. Returns (range_str, low, high)."""
    # Chinese reference range patterns: 参考范围、参考值、正常范围、正常值
    patterns = [
        r"(?:参考范围|参考值|正常范围|正常值|參考範圍|參考值)[：:]\s*([^\s,，]+)",
        r"(?:参考范围|参考值|正常范围|正常值|參考範圍|參考值)\s+([^\s,，]+)",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            range_str = match.group(1).strip()
            # Try to parse low-high range
            range_match = re.match(r"([\d.]+)\s*[-~到至]\s*([\d.]+)", range_str)
            if range_match:
                return (range_str, range_match.group(1), range_match.group(2))
            return (range_str, None, None)

    # Also try inline range pattern like "3.9-6.1"
    range_match = re.search(r"([\d.]+)\s*[-~]\s*([\d.]+)(?:\s*(?:mmol/L|umol/L|mg/dL|µmol/L|%))?", text)
    if range_match:
        range_str = f"{range_match.group(1)}-{range_match.group(2)}"
        return (range_str, range_match.group(1), range_match.group(2))

    return (None, None, None)


def _determine_status(value: float, ref_low, ref_high) -> str:
    """Determine if a value is low, normal, or high against reference range."""
    low: float | None = None
    high: float | None = None
    try:
        if ref_low is not None:
            low = float(ref_low)
    except (ValueError, TypeError):
        pass
    try:
        if ref_high is not None:
            high = float(ref_high)
    except (ValueError, TypeError):
        pass

    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    if low is not None or high is not None:
        return "normal"
    return "unknown"


def extract_lab_values_from_text(ocr_text: str) -> dict[str, Any]:
    """Extract common lab values from unstructured Chinese OCR text.

    Returns a dict keyed by lab item code with {item, value, unit, reference_range, status}.
    Handles common OCR errors and both simplified/traditional Chinese.
    """
    if not ocr_text or not ocr_text.strip():
        return {}

    text = _apply_ocr_fixes(ocr_text)
    text = _normalize_chinese(text)

    # Normalize horizontal whitespace only (preserve newlines for line-based parsing)
    text = re.sub(r"[ \t]+", " ", text)

    # Try to find structured lines first (Chinese lab report format)
    parsed_lines = parse_chinese_lab_report(text)
    if parsed_lines:
        results: dict[str, Any] = {}
        for entry in parsed_lines:
            mapped_code = _map_item_name_to_code(entry["item"])
            if mapped_code:
                results[mapped_code] = entry
        return results

    # Fall back to per-item regex extraction
    results: dict[str, Any] = {}
    for code, patterns in LAB_PATTERNS.items():
        entry = _extract_item_by_patterns(text, patterns, code)
        if entry:
            results[code] = entry

    return results


def _map_item_name_to_code(item_name: str) -> str | None:
    """Map a Chinese item name to standard lab code."""
    normalized = item_name.strip().upper()
    mapping: dict[str, str] = {
        "GLU": "fpg", "FPG": "fpg", "BS": "fpg",
        "HBA1C": "hba1c", "HBA1C": "hba1c",
        "TC": "tc", "CHO": "tc", "CHOL": "tc",
        "LDL": "ldl", "LDL-C": "ldl",
        "HDL": "hdl", "HDL-C": "hdl",
        "TG": "tg", "TRIG": "tg",
        "CR": "creatinine", "CRE": "creatinine", "CREA": "creatinine",
        "BUN": "bun", "UREA": "bun",
        "UACR": "uacr", "ACR": "uacr",
        "EGFR": "egfr", "GFR": "egfr",
    }
    if normalized in mapping:
        return mapping[normalized]

    # Try fuzzy matching against pattern list
    for code, patterns in LAB_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, item_name, re.IGNORECASE):
                return code

    return None


def _extract_item_by_patterns(text: str, patterns: list[str], code: str) -> dict[str, Any] | None:
    """Try to extract a single lab item by its patterns."""
    # Common unit maps
    unit_map: dict[str, str] = {
        "fpg": "mmol/L", "hba1c": "%", "tc": "mmol/L",
        "ldl": "mmol/L", "hdl": "mmol/L", "tg": "mmol/L",
        "creatinine": "umol/L", "bun": "mmol/L", "uacr": "mg/g",
        "egfr": "mL/min/1.73m2",
    }

    for pat in patterns:
        # Build full regex: item name, then optional junk, then a number, then optional unit
        full_pat = rf"({pat})[：:\s]*(?:[\d.]+\s*(?:mmol/L|umol/L|mg/dL|mg/g|%|mL/min)|[^\n]+)"
        match = re.search(full_pat, text, re.IGNORECASE)
        if not match:
            # Try line-based approach
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if re.search(pat, line, re.IGNORECASE):
                    value = _extract_number(line)
                    if value is None:
                        continue
                    # Try to find unit
                    unit_match = re.search(
                        r"(mmol/L|umol/L|mg/dL|mg/g|mg/ml|g/L|%|mL/min|µmol/L|U/L|ng/mL|mEq/L)",
                        line, re.IGNORECASE,
                    )
                    unit = unit_match.group(1) if unit_match else unit_map.get(code, "")
                    ref_range, ref_low, ref_high = _find_reference_range(line)
                    status = _determine_status(value, ref_low, ref_high)
                    return {
                        "item": pat,
                        "value": value,
                        "unit": unit,
                        "reference_range": ref_range,
                        "status": status,
                    }
            continue

        # Extract value from matched region
        matched_text = match.group(0)
        value = _extract_number(matched_text)
        if value is None:
            continue

        unit_match = re.search(
            r"(mmol/L|umol/L|mg/dL|mg/g|mg/ml|g/L|%|mL/min|µmol/L|U/L|ng/mL|mEq/L)",
            matched_text, re.IGNORECASE,
        )
        unit = unit_match.group(1) if unit_match else unit_map.get(code, "")
        ref_range, ref_low, ref_high = _find_reference_range(matched_text)
        status = _determine_status(value, ref_low, ref_high)

        return {
            "item": pat,
            "value": value,
            "unit": unit,
            "reference_range": ref_range,
            "status": status,
        }

    return None


def parse_chinese_lab_report(text: str) -> list[dict[str, Any]]:
    """Parse a Chinese lab report in the format: 项目名 结果 单位 参考范围.

    Detects lines containing a lab item name followed by numeric values.
    Returns a list of structured dicts with {item, value, unit, reference_range, status}.
    Handles both simplified and traditional Chinese characters.
    """
    if not text or not text.strip():
        return []

    text = _apply_ocr_fixes(text)
    text = _normalize_chinese(text)

    results: list[dict[str, Any]] = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Skip headers and footers
        if re.search(r"(项目|項目|检验|检验|报告|報告|姓名|性别|科室|日期|标本|序号|编号)", line) and not re.search(r"\d", line):
            continue

        # Skip pure label lines
        if re.match(r"^[^\d]+$", line) and len(line) < 15:
            continue

        entry = _parse_single_line(line)
        if entry:
            results.append(entry)

    return results


def _parse_single_line(line: str) -> dict[str, Any] | None:
    """Parse a single line of Chinese lab report data.

    Expected format: 项目名 [缩写] 数值 单位 参考范围
    Example: 空腹血糖(GLU) 6.5 mmol/L 3.9-6.1
    """
    # Find the numeric value and its position in the line using regex
    num_match = re.search(r"(?:^|[\s(（,，])(\d+\.?\d*)", line)
    if not num_match:
        return None

    value_str = num_match.group(1)
    try:
        value = float(value_str)
    except ValueError:
        return None

    value_start = num_match.start(1)
    value_end = num_match.end(1)

    # Extract the unit after the value
    after_val_match = re.search(
        r"\s*([^\s,，\d]*)",
        line[value_end:],
    )
    unit = ""
    if after_val_match:
        unit_candidate = after_val_match.group(1).strip()
        if re.match(
            r"^(mmol/L|umol/L|mg/dL|mg/g|mg/ml|g/L|%|mL/min|µmol/L|U/L|ng/mL|mEq/L)$",
            unit_candidate,
            re.IGNORECASE,
        ):
            unit = unit_candidate

    # Extract item name — everything before the numeric value
    item_part = line[:value_start].strip()
    # Clean up item name: remove trailing punctuation, parentheses
    item_part = re.sub(r"[：:，,]\s*$", "", item_part)
    item_part = item_part.strip()

    if not item_part:
        return None

    # Extract reference range from text after the value
    after_value = line[value_end:]
    ref_range, ref_low, ref_high = _find_reference_range(after_value)
    if not ref_range:
        # Also try the full line
        ref_range, ref_low, ref_high = _find_reference_range(line)

    # Determine status against reference range or common clinical thresholds
    status = _determine_status(value, ref_low, ref_high)

    # If no reference range but we know clinically meaningful thresholds
    if status == "unknown":
        status = _clinical_status_from_item_name(item_part, value)

    return {
        "item": item_part,
        "value": value,
        "unit": unit,
        "reference_range": ref_range,
        "status": status,
    }


def _clinical_status_from_item_name(item_name: str, value: float) -> str:
    """Determine clinical status based on common T2DM guideline thresholds."""
    normalized = item_name.strip().upper()

    # Fasting glucose thresholds
    if any(kw in normalized for kw in ["GLU", "FPG", "血糖", "空腹"]):
        if value < 3.9:
            return "low"
        if value < 6.1:
            return "normal"
        if value < 7.0:
            return "high"
        return "high"

    # HbA1c thresholds
    if any(kw in normalized for kw in ["HBA1C", "糖化", "A1C"]):
        if value < 5.7:
            return "normal"
        if value < 6.5:
            return "high"
        if value < 8.0:
            return "high"
        return "high"

    # Total cholesterol
    if any(kw in normalized for kw in ["TC", "CHO", "胆固醇", "膽固醇"]):
        if value < 5.2:
            return "normal"
        if value < 6.2:
            return "high"
        return "high"

    # LDL
    if any(kw in normalized for kw in ["LDL", "低密度"]):
        if value < 3.4:
            return "normal"
        if value < 4.1:
            return "high"
        return "high"

    # HDL (higher is better)
    if any(kw in normalized for kw in ["HDL", "高密度"]):
        if value >= 1.0:
            return "normal"
        return "low"

    # Triglycerides
    if any(kw in normalized for kw in ["TG", "甘油", "三酸"]):
        if value < 1.7:
            return "normal"
        if value < 2.3:
            return "high"
        return "high"

    # Creatinine
    if any(kw in normalized for kw in ["CR", "肌酐", "肌酸酐"]):
        if value > 133:
            return "high"
        return "normal"

    # eGFR
    if any(kw in normalized for kw in ["EGFR", "GFR", "肾小球"]):
        if value >= 90:
            return "normal"
        if value >= 60:
            return "high"
        if value >= 30:
            return "high"
        return "high"

    return "unknown"
