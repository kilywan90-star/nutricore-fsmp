import pytest
from datetime import datetime
from src.services.alert_engine import check_glucose_alerts, check_compliance_alerts


def test_check_fasting_hyperglycemia_alert():
    records = [
        {"value_mmol_l": 7.5, "measure_type": "fasting", "recorded_at": datetime(2026, 5, 30)},
        {"value_mmol_l": 8.0, "measure_type": "fasting", "recorded_at": datetime(2026, 5, 29)},
        {"value_mmol_l": 7.8, "measure_type": "fasting", "recorded_at": datetime(2026, 5, 28)},
    ]
    alerts = check_glucose_alerts(records)
    consecutive_alerts = [a for a in alerts if a.get("id") == "alert-003"]
    assert len(consecutive_alerts) >= 1


def test_check_critical_hyperglycemia():
    records = [
        {"value_mmol_l": 18.0, "measure_type": "fasting", "recorded_at": datetime(2026, 5, 30)},
    ]
    alerts = check_glucose_alerts(records)
    critical = [a for a in alerts if a.get("severity") == "critical"]
    assert len(critical) >= 1


def test_check_hypoglycemia():
    records = [
        {"value_mmol_l": 3.2, "measure_type": "random", "recorded_at": datetime(2026, 5, 30)},
    ]
    alerts = check_glucose_alerts(records)
    hypo = [a for a in alerts if "低血糖" in a.get("title", "")]
    assert len(hypo) >= 1


def test_no_alerts_normal():
    records = [
        {"value_mmol_l": 5.5, "measure_type": "fasting", "recorded_at": datetime(2026, 5, 30)},
        {"value_mmol_l": 6.0, "measure_type": "fasting", "recorded_at": datetime(2026, 5, 29)},
    ]
    alerts = check_glucose_alerts(records)
    assert len(alerts) == 0


def test_check_missed_logging():
    alerts = check_compliance_alerts(
        last_log_date=datetime(2026, 5, 25),
        today=datetime(2026, 5, 30),
        expected_logs_per_day=3,
    )
    assert len(alerts) >= 1
    assert "未记录血糖" in alerts[0]["title"]
