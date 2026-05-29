"""
钉钉集成模块：创建待办、发送消息。
依赖: pip install requests
钉钉开放平台文档: https://open.dingtalk.com/
"""

import os
import json
import time
import hmac
import hashlib
import base64
import urllib.parse

import requests


class DingTalkClient:
    """
    钉钉 API 客户端。

    环境变量:
      DINGTALK_APP_KEY     - 应用 AppKey
      DINGTALK_APP_SECRET  - 应用 AppSecret
      DINGTALK_AGENT_ID    - 应用 AgentId
      DINGTALK_ROBOT_TOKEN - 机器人 Webhook Token（发消息用，可选）
    """

    def __init__(self):
        self.app_key = os.getenv("DINGTALK_APP_KEY", "")
        self.app_secret = os.getenv("DINGTALK_APP_SECRET", "")
        self.agent_id = os.getenv("DINGTALK_AGENT_ID", "")
        self._access_token = None
        self._token_expires_at = 0

    def _get_access_token(self) -> str:
        """获取钉钉 access_token，自动缓存。"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = "https://oapi.dingtalk.com/gettoken"
        params = {"appkey": self.app_key, "appsecret": self.app_secret}
        resp = requests.get(url, params=params)
        data = resp.json()

        if data.get("errcode") != 0:
            raise RuntimeError(f"获取钉钉 access_token 失败: {data}")

        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"] - 60
        return self._access_token

    def create_todo(self, todo_item: dict, user_id: str) -> dict:
        """
        创建钉钉待办。

        todo_item 格式（来自 todo.py 的输出）:
          {
            "待办标题": "...",
            "详细说明": "...",
            "截止时间": "YYYY-MM-DD",
            "优先级": "高 | 中 | 低",
            ...
          }

        user_id: 钉钉用户 ID（可通过通讯录 API 获取）
        """
        token = self._get_access_token()
        url = "https://oapi.dingtalk.com/topapi/workrecord/add"

        body = {
            "userid": user_id,
            "create_time": int(time.time() * 1000),
            "title": todo_item.get("待办标题", "待办事项"),
            "url": "",  # 可配置跳转链接
            "formItemList": [
                {"title": "详细说明", "content": todo_item.get("详细说明", "")},
                {"title": "优先级", "content": todo_item.get("优先级", "中")},
                {"title": "截止时间", "content": todo_item.get("截止时间", "")},
                {"title": "来源", "content": todo_item.get("关联来源", "")},
            ],
        }

        resp = requests.post(
            url,
            params={"access_token": token},
            json=body,
        )
        return resp.json()

    def send_group_message(self, content: str, robot_token: str = None) -> dict:
        """
        通过钉钉机器人发送群消息（Markdown 格式）。

        content: Markdown 格式消息内容
        robot_token: 机器人 Webhook token，不传则用环境变量
        """
        token = robot_token or os.getenv("DINGTALK_ROBOT_TOKEN", "")
        if not token:
            raise ValueError("请设置 DINGTALK_ROBOT_TOKEN 环境变量")

        url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        body = {
            "msgtype": "markdown",
            "markdown": {
                "title": "政策文档分析通知",
                "text": content,
            },
        }

        resp = requests.post(url, json=body)
        return resp.json()

    def send_work_notice(self, user_id: str, content: str) -> dict:
        """
        通过工作通知发送消息给指定用户。
        """
        token = self._get_access_token()
        url = f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"

        body = {
            "agent_id": int(self.agent_id),
            "userid_list": user_id,
            "msg": {
                "msgtype": "markdown",
                "markdown": {
                    "title": "政策文档分析通知",
                    "text": content,
                },
            },
        }

        resp = requests.post(
            url,
            params={"access_token": token},
            json=body,
        )
        return resp.json()

    def get_user_by_mobile(self, mobile: str) -> str:
        """根据手机号获取钉钉用户 ID。"""
        token = self._get_access_token()
        url = "https://oapi.dingtalk.com/topapi/v2/user/getbymobile"
        resp = requests.post(
            url,
            params={"access_token": token},
            json={"mobile": mobile},
        )
        data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"获取钉钉用户失败: {data}")
        return data["result"]["userid"]


def format_todos_as_markdown(todos: list, source_file: str) -> str:
    """将待办列表格式化为钉钉 Markdown 消息。"""
    lines = [
        f"## 📋 政策文件分析 - {source_file}",
        "",
    ]

    for i, todo in enumerate(todos, 1):
        priority_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(todo.get("优先级", "中"), "⚪")
        lines.extend([
            f"---",
            f"### {priority_emoji} 待办 {i}：{todo.get('待办标题', '')}",
            f"",
            f"**详细说明**：{todo.get('详细说明', '')}",
            f"**责任部门**：{todo.get('责任部门', '')}  ",
            f"**责任人角色**：{todo.get('责任人角色', '')}  ",
            f"**截止时间**：{todo.get('截止时间', '')}  ",
            f"**需提交材料**：{'、'.join(todo.get('需提交材料', []))}",
            f"**关联来源**：{todo.get('关联来源', '')}",
            f"",
        ])

    return "\n".join(lines)


if __name__ == "__main__":
    # 测试：创建一条待办
    client = DingTalkClient()
    test_todo = {
        "待办标题": "提交Q2返利申报表",
        "详细说明": "请各门店于7月5日前完成Q2返利数据填报并上传至财务系统。",
        "截止时间": "2026-07-05",
        "优先级": "高",
        "关联来源": "长城Q2返利政策.pdf - 第3条",
    }

    try:
        # 需要先在环境变量配置钉钉参数
        result = client.create_todo(test_todo, user_id="test_user")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"钉钉 API 调用失败（预期内，需配置环境变量）: {e}")
        print("配置方法: 设置 DINGTALK_APP_KEY, DINGTALK_APP_SECRET, DINGTALK_AGENT_ID")
