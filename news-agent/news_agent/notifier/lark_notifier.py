"""飞书通知模块。

通过 lark-cli 发送消息通知。默认发送到与当前 bot/user 的私聊，
也可以通过环境变量 LARK_CHAT_ID 指定目标群聊。
"""

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from news_agent.utils.logger import logger


def send_run_summary(run_info: dict) -> bool:
    """Send a run summary notification via Lark.

    run_info keys:
        status: 'success' | 'partial' | 'failed'
        collected: int
        after_dedup: int
        generated: int
        failed: int
        errors: list[str]
        drafts: list[str]  # draft file paths
    """
    try:
        message = _build_message(run_info)
        return _send_lark_message(message)
    except Exception as e:
        logger.error(f"Failed to send Lark notification: {e}")
        return False


def _build_message(run_info: dict) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_emoji = {
        "success": "OK",
        "partial": "WARN",
        "failed": "ERROR",
    }.get(run_info.get("status", "failed"), "ERROR")

    lines = [
        f"[{status_emoji}] 新闻智能体运行报告",
        f"时间: {now}",
        f"采集: {run_info.get('collected', 0)}条",
        f"去重: {run_info.get('after_dedup', 0)}条",
        f"生成: {run_info.get('generated', 0)}条",
        f"失败: {run_info.get('failed', 0)}条",
    ]

    errors = run_info.get("errors", [])
    if errors:
        lines.append("错误: " + "; ".join(e[:80] for e in errors[:3]))

    drafts = run_info.get("drafts", [])
    if drafts:
        lines.append("草稿: " + ", ".join(Path(d).name for d in drafts[:3]))

    return " | ".join(lines)


def _send_lark_message(message: str) -> bool:
    """Send message via lark-cli. Falls back to structured text if lark-cli unavailable."""
    chat_id = os.getenv("LARK_CHAT_ID", "")

    try:
        lark_cli = os.path.expandvars(r"%APPDATA%\npm\lark-cli.cmd")
        if not os.path.exists(lark_cli):
            lark_cli = "lark-cli"
        cmd = [lark_cli, "im", "+messages-send", "--text", message]
        if chat_id:
            cmd.extend(["--chat-id", chat_id])
        else:
            cmd.extend(["--as", "user", "--user-id", "ou_76b7971b5a21d71fe85d801af6ceaf1e"])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if result.returncode != 0:
            logger.warning(f"lark-cli returned non-zero: {result.stderr}")
            return False
        logger.info("Lark notification sent successfully")
        return True
    except FileNotFoundError:
        logger.warning("lark-cli not found, notification stored in log only")
        return False
    except subprocess.TimeoutExpired:
        logger.error("lark-cli timed out")
        return False
