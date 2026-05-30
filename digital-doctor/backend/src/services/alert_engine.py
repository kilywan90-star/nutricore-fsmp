from datetime import datetime


def check_glucose_alerts(records: list[dict]) -> list[dict]:
    alerts: list[dict] = []
    if not records:
        return alerts

    records.sort(key=lambda r: r.get("recorded_at", datetime.min), reverse=True)

    # Check latest for critical hyper/hypoglycemia
    latest = records[0]
    value = latest.get("value_mmol_l", 0)
    if value >= 16.7:
        alerts.append({
            "id": "alert-001", "alert_type": "severe_hyperglycemia", "severity": "critical",
            "title": "严重高血糖预警", "detail": f"血糖{value}mmol/L>=16.7，需立即处理",
            "reference_guideline": "中国2型糖尿病防治指南(2024版) §12.1",
            "value": value,
        })
    elif value <= 3.9:
        alerts.append({
            "id": "alert-002", "alert_type": "hypoglycemia", "severity": "warning",
            "title": "低血糖预警", "detail": f"血糖{value}mmol/L<=3.9，低血糖",
            "reference_guideline": "中国2型糖尿病防治指南(2024版) §12.2",
            "value": value,
        })

    # Check consecutive 3-day high fasting glucose
    fasting_records = [r for r in records if r.get("measure_type") == "fasting"]
    if len(fasting_records) >= 3:
        recent_3 = fasting_records[:3]
        if all(r.get("value_mmol_l", 0) >= 7.0 for r in recent_3):
            alerts.append({
                "id": "alert-003", "alert_type": "consecutive_high_fpg", "severity": "warning",
                "title": "空腹血糖持续偏高", "detail": "连续3天空腹血糖>=7.0mmol/L",
                "reference_guideline": "中国2型糖尿病防治指南(2024版) §8.2",
            })

    return alerts


def check_compliance_alerts(
    last_log_date: datetime,
    today: datetime,
    expected_logs_per_day: int = 3,
) -> list[dict]:
    alerts = []
    days_since = (today - last_log_date).days
    if days_since >= 2:
        alerts.append({
            "id": "compliance-001", "alert_type": "missed_logging", "severity": "warning",
            "title": f"连续{days_since}天未记录血糖",
            "detail": f"上次记录时间：{last_log_date.strftime('%m月%d日')}，请提醒患者恢复血糖监测",
            "reference_guideline": "中国2型糖尿病防治指南(2024版) §10.1",
        })
    return alerts
