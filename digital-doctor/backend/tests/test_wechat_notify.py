"""Tests for WeChat notification service.

Covers:
- Subscribe message format validation
- Medication reminder template structure
"""

import pytest

from src.services.wechat_notify import (
    build_medication_reminder_message,
    build_glucose_alert_message,
    send_subscribe_message,
    MEDICATION_REMINDER_TEMPLATE,
    GLUCOSE_ALERT_TEMPLATE,
    SubscribeMessageTemplate,
)


def test_medication_reminder_template_format():
    """Medication reminder message must follow WeChat subscribe-message schema:
    {template_id: str, data: {key: {value: str}}}
    """
    msg = build_medication_reminder_message(
        drug_name="二甲双胍",
        dosage="500mg",
        time_str="2026-05-30 08:00",
        note="请按时服药",
    )

    assert isinstance(msg, SubscribeMessageTemplate)
    assert msg.template_id == MEDICATION_REMINDER_TEMPLATE

    # Every data value must be a dict with a 'value' key (WeChat API spec)
    for key, val in msg.data.items():
        assert isinstance(val, dict), f"data.{key} should be a dict"
        assert "value" in val, f"data.{key} should contain 'value'"

    # Verify key fields
    assert "二甲双胍 500mg" in msg.data["thing1"]["value"]
    assert msg.data["time2"]["value"] == "2026-05-30 08:00"
    assert msg.data["thing3"]["value"] == "请按时服药"


def test_glucose_alert_template_format():
    """Glucose alert message must follow WeChat subscribe-message schema with
    correct alert type and glucose value formatting.
    """
    msg = build_glucose_alert_message(
        glucose_value=13.5,
        alert_type="高血糖",
        time_str="2026-05-30 09:30",
        note="请及时处理",
    )

    assert msg.template_id == GLUCOSE_ALERT_TEMPLATE

    # Verify data structure
    for key, val in msg.data.items():
        assert isinstance(val, dict), f"data.{key} should be a dict"
        assert "value" in val, f"data.{key} should contain 'value'"

    assert "高血糖" in msg.data["thing1"]["value"]
    assert "13.5" in msg.data["number2"]["value"]
    assert msg.data["time3"]["value"] == "2026-05-30 09:30"
    assert msg.data["thing4"]["value"] == "请及时处理"
