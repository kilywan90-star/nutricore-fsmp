# digital-doctor/backend/src/services/glucose_tracker.py
from datetime import datetime
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
