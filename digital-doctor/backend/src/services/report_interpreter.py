# digital-doctor/backend/src/services/report_interpreter.py
from typing import Any


GLUCOSE_THRESHOLDS = {
    "fpg": {"normal": (3.9, 6.1), "impaired": (6.1, 7.0)},
    "ppg_2h": {"normal": (0, 7.8), "impaired": (7.8, 11.1)},
    "hba1c": {"normal": (0, 6.5), "impaired": (6.5, 7.0)},
}

LIPID_THRESHOLDS = {
    "tc": {"normal": (0, 5.2), "borderline": (5.2, 6.2)},
    "ldl": {"normal": (0, 3.4), "borderline": (3.4, 4.1)},
    "hdl": {"normal": (1.0, 99), "low": (0, 1.0)},
    "tg": {"normal": (0, 1.7), "borderline": (1.7, 2.3)},
}


def _classify_value(value: float, thresholds: dict) -> str:
    for status, (lo, hi) in thresholds.items():
        if lo <= value < hi:
            return status
    return "abnormal"


def interpret_lab_report(report_type: str, results: dict[str, Any]) -> dict:
    items = []
    overall_max = "normal"

    if report_type in ("blood_glucose_panel", "hba1c_only"):
        for key, thresholds in GLUCOSE_THRESHOLDS.items():
            if key in results:
                status = _classify_value(results[key], thresholds)
                if status == "abnormal":
                    overall_max = "abnormal"
                elif status == "impaired" and overall_max == "normal":
                    overall_max = "impaired"
                items.append({"item": key, "value": results[key], "status": status})

    if report_type == "lipid_panel":
        for key, thresholds in LIPID_THRESHOLDS.items():
            if key in results:
                status = _classify_value(results[key], thresholds)
                if status != "normal":
                    overall_max = "abnormal"
                items.append({"item": key, "value": results[key], "status": status})

    status_labels = {"normal": "正常", "impaired": "临界异常", "abnormal": "异常", "unknown": "未知"}
    interpretation = _generate_interpretation(report_type, overall_max, results)

    return {
        "status": overall_max,
        "status_label": status_labels.get(overall_max, "未知"),
        "items": items,
        "interpretation": interpretation,
    }


def _generate_interpretation(report_type: str, status: str, results: dict) -> str:
    if status == "normal":
        return "检查结果均在正常范围。继续维持当前生活方式和治疗方案。"
    if report_type == "blood_glucose_panel":
        parts = []
        fpg = results.get("fpg")
        hba1c = results.get("hba1c")
        if fpg is not None:
            if fpg >= 7.0:
                parts.append(f"空腹血糖{fpg}mmol/L，高于诊断标准(≥7.0)")
            elif fpg >= 6.1:
                parts.append(f"空腹血糖{fpg}mmol/L，处于糖尿病前期范围(6.1-7.0)")
        if hba1c is not None:
            if hba1c >= 7.0:
                parts.append(f"糖化血红蛋白{hba1c}%，提示近3月血糖控制未达标(目标<7.0%)")
            elif hba1c >= 6.5:
                parts.append(f"糖化血红蛋白{hba1c}%，已达糖尿病诊断标准(≥6.5%)")
        parts.append("建议定期监测血糖，遵医嘱调整治疗方案。")
        return " ".join(parts)
    return "部分指标异常，建议到内分泌科就诊评估。"
