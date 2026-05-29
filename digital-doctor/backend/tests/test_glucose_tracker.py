import pytest
from src.services.glucose_tracker import (
    analyze_glucose_trend,
    calculate_glucose_stats,
    TimeInRange,
)


def test_calculate_stats_empty():
    stats = calculate_glucose_stats([])
    assert stats["count"] == 0
    assert stats["avg"] is None


def test_calculate_stats_with_data():
    records = [6.5, 7.2, 5.8, 8.0, 6.1]
    stats = calculate_glucose_stats(records)
    assert stats["count"] == 5
    assert 6.6 < stats["avg"] < 6.8
    assert stats["max"] == 8.0
    assert stats["min"] == 5.8


def test_time_in_range_all_in_range():
    records = [5.0, 6.0, 7.0, 6.5, 5.5]
    tir = TimeInRange(records)
    assert tir.in_range_pct > 80


def test_time_in_range_with_highs():
    records = [5.0, 12.0, 6.0, 14.0, 7.0]
    tir = TimeInRange(records)
    assert tir.above_range_pct > 30


def test_time_in_range_with_lows():
    records = [3.0, 5.0, 3.5, 6.0, 4.0]
    tir = TimeInRange(records)
    assert tir.below_range_pct > 30


def test_analyze_trend_rising():
    records = [
        {"value": 6.0, "date": "2026-05-01"},
        {"value": 6.5, "date": "2026-05-08"},
        {"value": 7.0, "date": "2026-05-15"},
        {"value": 7.5, "date": "2026-05-22"},
    ]
    trend = analyze_glucose_trend(records)
    assert trend["direction"] == "rising"


def test_analyze_trend_stable():
    records = [
        {"value": 6.5, "date": "2026-05-01"},
        {"value": 6.3, "date": "2026-05-08"},
        {"value": 6.7, "date": "2026-05-15"},
        {"value": 6.4, "date": "2026-05-22"},
    ]
    trend = analyze_glucose_trend(records)
    assert trend["direction"] == "stable"
