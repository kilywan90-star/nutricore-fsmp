from typing import Any


def calculate_glucose_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "avg": None, "max": None, "min": None, "std": None}
    n = len(values)
    avg = sum(values) / n
    variance = sum((v - avg) ** 2 for v in values) / n
    return {
        "count": n,
        "avg": round(avg, 1),
        "max": round(max(values), 1),
        "min": round(min(values), 1),
        "std": round(variance ** 0.5, 1),
    }


class TimeInRange:
    TARGET_LOW = 3.9
    TARGET_HIGH = 10.0

    def __init__(self, values: list[float]):
        self.total = len(values)
        if self.total == 0:
            self.in_range_pct = 0
            self.above_range_pct = 0
            self.below_range_pct = 0
            return
        in_range = sum(1 for v in values if self.TARGET_LOW <= v <= self.TARGET_HIGH)
        above = sum(1 for v in values if v > self.TARGET_HIGH)
        below = sum(1 for v in values if v < self.TARGET_LOW)
        self.in_range_pct = round(in_range / self.total * 100, 1)
        self.above_range_pct = round(above / self.total * 100, 1)
        self.below_range_pct = round(below / self.total * 100, 1)


def analyze_glucose_trend(records: list[dict]) -> dict:
    if len(records) < 3:
        return {"direction": "insufficient_data", "change_rate": None}
    recent = records[-3:]
    values = [r["value"] for r in recent]

    if all(values[i] < values[i + 1] for i in range(len(values) - 1)):
        direction = "rising"
    elif all(values[i] > values[i + 1] for i in range(len(values) - 1)):
        direction = "falling"
    else:
        direction = "stable"

    first_avg = sum(values[:2]) / 2
    last_avg = sum(values[-2:]) / 2
    change_rate = round((last_avg - first_avg) / first_avg * 100, 1) if first_avg else 0

    return {"direction": direction, "change_rate": change_rate, "recent_values": values}


def merge_cgm_with_manual(
    manual_records: list[dict],
    cgm_records: list[dict],
) -> list[dict]:
    """Merge manual glucose records with CGM data into a unified glucose view.

    Manual records take precedence for any timestamp within 5 minutes of a CGM reading.
    Both are sorted chronologically.

    Args:
        manual_records: list of dicts with keys 'value_mmol_l', 'recorded_at', 'measure_type', 'notes'
        cgm_records: list of dicts with keys 'value_mmol_l', 'timestamp', 'trend_direction', 'device_type'

    Returns unified list sorted by timestamp, each with 'value_mmol_l', 'timestamp', 'source', and optional fields.
    """
    from datetime import datetime

    merged: list[dict] = []

    for mr in manual_records:
        ts = mr.get("recorded_at")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        merged.append({
            "value_mmol_l": mr["value_mmol_l"],
            "timestamp": ts,
            "source": "manual",
            "measure_type": mr.get("measure_type", "random"),
            "notes": mr.get("notes"),
        })

    manual_times = [m["timestamp"] for m in merged]
    for cr in cgm_records:
        ts = cr.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if any(abs((ts - mt).total_seconds()) < 300 for mt in manual_times):
            continue
        merged.append({
            "value_mmol_l": cr["value_mmol_l"],
            "timestamp": ts,
            "source": "cgm",
            "trend_direction": cr.get("trend_direction"),
            "device_type": cr.get("device_type"),
        })

    merged.sort(key=lambda r: r["timestamp"])
    return merged
