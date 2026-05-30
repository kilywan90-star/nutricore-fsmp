"""CGM data file parsers for major device brands.

Supports:
- Freestyle Libre CSV (Chinese headers)
- Dexcom Clarity CSV
- Generic JSON format
"""

import csv
import json
import re
from datetime import datetime
from io import StringIO
from typing import Any

MGDL_TO_MMOL = 18.018


def _parse_timestamp(ts_str: str) -> datetime:
    """Try common CGM timestamp formats."""
    ts_str = ts_str.strip().strip('"')
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d-%m-%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    # ISO format with timezone
    try:
        ts_str_clean = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_str_clean)
    except (ValueError, AttributeError):
        pass
    raise ValueError(f"Cannot parse timestamp: {ts_str}")


def _parse_value(value_str: str, unit: str) -> float:
    """Parse a glucose value and return mmol/L."""
    v = float(value_str.strip().strip('"'))
    if unit.lower() in ("mg/dl", "mgdl", "mg_dl"):
        return round(v / MGDL_TO_MMOL, 1)
    return round(v, 1)


def _map_trend_direction(trend_raw: str) -> str | None:
    """Map vendor trend indicators to standard directions."""
    if not trend_raw:
        return None
    t = trend_raw.strip().lower()
    rising = {"rising", "up", "↑", "↗", "rapidly_rising", "double_up"}
    falling = {"falling", "down", "↓", "↘", "rapidly_falling", "double_down"}
    stable = {"stable", "→", "steady", "flat", "constant"}
    if t in rising:
        return "rising"
    if t in falling:
        return "falling"
    if t in stable:
        return "stable"
    return t


def parse_freestyle_libre_csv(content: str) -> list[dict[str, Any]]:
    """Parse Abbott Freestyle Libre CSV export.

    Freestyle Libre CSV typically has headers like:
    设备序列号,时间戳,记录类型,血糖历史值(mg/dL),...

    We handle both the 'historical glucose' row type and any line with a numeric value.
    """
    reader = csv.reader(StringIO(content))
    rows = list(reader)
    if not rows:
        return []

    # Find header row — Libre exports often have metadata rows before data
    header_idx = 0
    for i, row in enumerate(rows):
        if not row:
            continue
        r0 = row[0].strip().lower() if row[0] else ""
        if r0 in ("设备序列号", "device serial", "serial number"):
            header_idx = i
            break

    headers = [h.strip().lower() for h in rows[header_idx]]
    headers_chinese_map = {
        "设备序列号": "device_serial",
        "时间戳": "timestamp",
        "记录类型": "record_type",
        "血糖历史值(mg/dl)": "glucose_mgdl",
        "血糖历史值（mg/dl）": "glucose_mgdl",
        "趋势箭头": "trend",
        "血糖扫描值(mg/dl)": "glucose_mgdl",
        "血糖扫描值（mg/dl）": "glucose_mgdl",
    }
    headers_eng_map = {
        "timestamp": "timestamp",
        "record type": "record_type",
        "historical glucose (mg/dl)": "glucose_mgdl",
        "scan glucose (mg/dl)": "glucose_mgdl",
        "trend arrow": "trend",
    }

    column_map = {}
    for i, h in enumerate(headers):
        if h in headers_chinese_map:
            column_map[headers_chinese_map[h]] = i
        elif h in headers_eng_map:
            column_map[headers_eng_map[h]] = i
        else:
            # Fuzzy match
            if "时间戳" in h or "timestamp" in h:
                column_map["timestamp"] = i
            elif "血糖" in h and ("mg/dl" in h or "mg_dl" in h):
                column_map["glucose_mgdl"] = i
            elif "趋势" in h or "trend" in h:
                column_map["trend"] = i

    readings = []
    for row in rows[header_idx + 1:]:
        if not row or len(row) < 2:
            continue
        ts_idx = column_map.get("timestamp")
        val_idx = column_map.get("glucose_mgdl")
        if ts_idx is None or val_idx is None:
            continue
        if val_idx >= len(row):
            continue
        try:
            ts = _parse_timestamp(row[ts_idx])
            value = _parse_value(row[val_idx], "mg/dl")
        except (ValueError, IndexError):
            continue

        trend_idx = column_map.get("trend")
        trend = _map_trend_direction(row[trend_idx]) if trend_idx is not None and trend_idx < len(row) else None

        readings.append({
            "timestamp": ts,
            "value_mmol_l": value,
            "trend_direction": trend,
            "raw_data": {headers[i]: v for i, v in enumerate(row) if i < len(headers)},
            "is_manual_calibration": False,
        })

    return readings


def parse_dexcom_csv(content: str) -> list[dict[str, Any]]:
    """Parse Dexcom Clarity CSV export.

    Dexcom Clarity typically exports:
    Timestamp,Event Type,Glucose Value (mg/dL),...
    """
    reader = csv.reader(StringIO(content))
    rows = list(reader)
    if not rows:
        return []

    headers = [h.strip().lower() for h in rows[0]]
    col_map = {}
    for i, h in enumerate(headers):
        h_clean = re.sub(r'[()（）]', '', h).strip().replace(' ', '_')
        if 'timestamp' in h_clean or 'time' in h_clean:
            col_map["timestamp"] = i
        elif 'glucose' in h_clean and 'value' in h_clean:
            col_map["glucose_mgdl"] = i
        elif 'event' in h_clean and 'type' in h_clean:
            col_map["event_type"] = i
        elif 'trend' in h_clean:
            col_map["trend"] = i

    if "timestamp" not in col_map or "glucose_mgdl" not in col_map:
        # Fallback: try column positions
        col_map["timestamp"] = 0
        col_map["glucose_mgdl"] = 1 if len(headers) > 1 else None

    readings = []
    for row in rows[1:]:
        if not row or len(row) < max(col_map.values()) + 1:
            continue
        ts_idx = col_map["timestamp"]
        val_idx = col_map["glucose_mgdl"]
        try:
            ts = _parse_timestamp(row[ts_idx])
            value = _parse_value(row[val_idx], "mg/dl")
        except (ValueError, IndexError):
            continue

        trend_idx = col_map.get("trend")
        trend = _map_trend_direction(row[trend_idx]) if trend_idx is not None and trend_idx < len(row) else None

        readings.append({
            "timestamp": ts,
            "value_mmol_l": value,
            "trend_direction": trend,
            "raw_data": {headers[i]: v for i, v in enumerate(row) if i < len(headers)},
            "is_manual_calibration": False,
        })

    return readings


def parse_generic_json(content: str) -> list[dict[str, Any]]:
    """Parse generic JSON CGM data format.

    Expected format:
    {
        "device": "xxx",
        "unit": "mmol/L" | "mg/dL",
        "readings": [
            {"ts": "2026-05-30T08:00:00", "value": 6.5, "trend": "stable"}
        ]
    }
    """
    data = json.loads(content)
    readings_list = data.get("readings", [])
    if not readings_list and isinstance(data, list):
        readings_list = data

    unit = data.get("unit", "mmol/L") if isinstance(data, dict) else "mmol/L"

    results = []
    for r in readings_list:
        ts_key = r.get("ts") or r.get("timestamp") or r.get("time") or r.get("datetime") or r.get("recorded_at")
        if not ts_key:
            continue
        try:
            ts = _parse_timestamp(str(ts_key))
        except (ValueError, IndexError):
            continue

        value_raw = r.get("value") or r.get("glucose") or r.get("glucose_value")
        if value_raw is None:
            continue
        unit_override = r.get("unit", unit)
        value = _parse_value(str(value_raw), unit_override)

        trend = _map_trend_direction(r.get("trend") or r.get("trend_direction") or r.get("arrow", ""))

        results.append({
            "timestamp": ts,
            "value_mmol_l": value,
            "trend_direction": trend,
            "raw_data": r,
            "is_manual_calibration": bool(r.get("calibration") or r.get("is_calibration") or False),
        })

    return results


def parse_cgm_file(content: bytes, file_format: str, filename: str = "") -> list[dict[str, Any]]:
    """Parse CGM file content based on format.

    Args:
        content: Raw file bytes
        file_format: One of 'freestyle_libre', 'dexcom', 'generic_json', or auto-detected from filename
        filename: Original filename for format auto-detection

    Returns list of reading dicts with keys: timestamp, value_mmol_l, trend_direction, raw_data, is_manual_calibration
    """
    text = content.decode("utf-8-sig").strip()

    # Auto-detect format if not specified or 'auto'
    if file_format in ("auto", "", None):
        if filename:
            fn_lower = filename.lower()
            if "libre" in fn_lower or "freestyle" in fn_lower:
                file_format = "freestyle_libre"
            elif "dexcom" in fn_lower or "clarity" in fn_lower:
                file_format = "dexcom"
            elif fn_lower.endswith(".json"):
                file_format = "generic_json"

    if file_format == "auto":
        if text.startswith("{"):
            file_format = "generic_json"
        else:
            first_line = text.split("\n")[0].lower()
            if "设备序列号" in first_line or "freestyle" in first_line:
                file_format = "freestyle_libre"
            elif "dexcom" in first_line or "timestamp" in first_line:
                file_format = "dexcom"
            else:
                file_format = "generic_json"

    if file_format == "freestyle_libre":
        return parse_freestyle_libre_csv(text)
    elif file_format == "dexcom":
        return parse_dexcom_csv(text)
    elif file_format == "generic_json":
        return parse_generic_json(text)
    else:
        raise ValueError(f"Unsupported CGM file format: {file_format}")


def detect_device_from_filename(filename: str) -> str:
    """Detect CGM device type from filename hints."""
    fn = filename.lower()
    if "libre" in fn or "freestyle" in fn:
        return "freestyle_libre"
    if "dexcom" in fn:
        if "g7" in fn:
            return "dexcom_g7"
        return "dexcom_g6"
    if "medtronic" in fn or "guardian" in fn:
        return "medtronic"
    if "sinocare" in fn or "三诺" in fn:
        return "sinocare"
    if "microtech" in fn or "微泰" in fn:
        return "microtech"
    return "unknown"
