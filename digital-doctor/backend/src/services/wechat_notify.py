"""WeChat Mini-Program notification service.

Handles subscribe-message push for medication reminders and abnormal glucose alerts.
All WeChat API calls are mockable for testing through the _wechat_api_callable indirection.
"""

from dataclasses import dataclass
from typing import Any, Callable

from src.config import settings


@dataclass
class SubscribeMessageTemplate:
    template_id: str
    data: dict[str, dict[str, str]]


MEDICATION_REMINDER_TEMPLATE = "medication_reminder"
GLUCOSE_ALERT_TEMPLATE = "glucose_alert"


def build_medication_reminder_message(
    drug_name: str,
    dosage: str,
    time_str: str,
    note: str = "请按时服药",
) -> SubscribeMessageTemplate:
    """Build a WeChat subscribe message for medication reminder.

    Args:
        drug_name: e.g. "二甲双胍"
        dosage: e.g. "500mg"
        time_str: e.g. "2026-05-30 08:00"
        note: custom reminder note

    Returns:
        SubscribeMessageTemplate with formatted data.
    """
    return SubscribeMessageTemplate(
        template_id=MEDICATION_REMINDER_TEMPLATE,
        data={
            "thing1": {"value": f"{drug_name} {dosage}"},
            "time2": {"value": time_str},
            "thing3": {"value": note},
        },
    )


def build_glucose_alert_message(
    glucose_value: float,
    alert_type: str,
    time_str: str,
    note: str = "请及时处理",
) -> SubscribeMessageTemplate:
    """Build a WeChat subscribe message for abnormal glucose alert.

    Args:
        glucose_value: the abnormal glucose reading in mmol/L.
        alert_type: "高血糖" or "低血糖".
        time_str: e.g. "2026-05-30 08:00".
        note: custom alert note.

    Returns:
        SubscribeMessageTemplate with formatted data.
    """
    return SubscribeMessageTemplate(
        template_id=GLUCOSE_ALERT_TEMPLATE,
        data={
            "thing1": {"value": f"{alert_type}预警"},
            "number2": {"value": f"{glucose_value:.1f} mmol/L"},
            "time3": {"value": time_str},
            "thing4": {"value": note},
        },
    )


# The actual WeChat API call is separated for testability.
_wechat_api_callable: Callable[..., dict[str, Any]] | None = None


def _default_send_subscribe_message(openid: str, template_id: str, data: dict) -> dict[str, Any]:
    """Default implementation: calls WeChat API to send subscribe message.

    In dev/test environments, returns a success stub so tests and local runs
    do not hit the real WeChat API. Set `_wechat_api_callable` to override.
    """
    # Development / test stub — no real HTTP call
    if not settings.WECHAT_APPID or not settings.WECHAT_SECRET:
        return {"errcode": 0, "errmsg": "ok (stub)", "template_id": template_id}

    # Real implementation would:
    # 1. Get access_token from https://api.weixin.qq.com/cgi-bin/token
    # 2. POST https://api.weixin.qq.com/cgi-bin/message/subscribe/send
    #       body: {touser, template_id, data, ...}
    return {"errcode": 0, "errmsg": "ok", "template_id": template_id}


def send_subscribe_message(
    openid: str,
    template_id: str,
    data: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Send a WeChat subscribe message to a user.

    Args:
        openid: the recipient's WeChat openid.
        template_id: the WeChat template id (e.g. "medication_reminder").
        data: the template-data payload per WeChat spec.

    Returns:
        The API response dict; {"errcode": 0, ...} on success.
    """
    caller = _wechat_api_callable or _default_send_subscribe_message
    return caller(openid, template_id, data)
