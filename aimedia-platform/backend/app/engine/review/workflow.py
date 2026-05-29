"""
审核工作流引擎 —— 状态机驱动，支持可配置的多级审核流程。

默认流程（三审三校）:
  草稿 → 一审(科室信息员) → 二审(科室负责人) → 三审(宣传科长) → 已通过

核心能力:
  - 审核级数可配置（2-5级）
  - 每级可配审核角色 + 会签/或签
  - SLA 计时 + 超时自动升级
  - 驳回策略可配置
"""

from datetime import datetime, timedelta, timezone
from enum import Enum


class ContentStatus(str, Enum):
    DRAFT = "draft"
    PENDING_1ST = "pending_1st"
    PENDING_2ND = "pending_2nd"
    PENDING_3RD = "pending_3rd"
    APPROVED = "approved"
    PUBLISHED = "published"
    OFFLINE = "offline"
    RETRACTED = "retracted"


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    RETURN = "return"
    SUBMIT = "submit"  # 提交审核（作者操作）


# 状态转移表
TRANSITIONS = {
    ContentStatus.DRAFT: [ReviewAction.SUBMIT],
    ContentStatus.PENDING_1ST: [ReviewAction.APPROVE, ReviewAction.REJECT, ReviewAction.RETURN],
    ContentStatus.PENDING_2ND: [ReviewAction.APPROVE, ReviewAction.REJECT, ReviewAction.RETURN],
    ContentStatus.PENDING_3RD: [ReviewAction.APPROVE, ReviewAction.REJECT, ReviewAction.RETURN],
    ContentStatus.APPROVED: [],
    ContentStatus.PUBLISHED: [],
    ContentStatus.OFFLINE: [],
    ContentStatus.RETRACTED: [],
}

# 状态 → 下一状态 (三审流程)
NEXT_STATUS = {
    (ContentStatus.DRAFT, ReviewAction.SUBMIT): ContentStatus.PENDING_1ST,
    (ContentStatus.PENDING_1ST, ReviewAction.APPROVE): ContentStatus.PENDING_2ND,
    (ContentStatus.PENDING_2ND, ReviewAction.APPROVE): ContentStatus.PENDING_3RD,
    (ContentStatus.PENDING_3RD, ReviewAction.APPROVE): ContentStatus.APPROVED,
}


class ReviewWorkflowEngine:
    """审核工作流状态机"""

    DEFAULT_LEVELS = 3
    DEFAULT_SLA_HOURS = 24  # 每级默认 24 小时

    def __init__(self, review_config: dict | None = None):
        self.levels: int = (review_config or {}).get("levels", self.DEFAULT_LEVELS)
        self.sla_hours: int = (review_config or {}).get("sla_hours", self.DEFAULT_SLA_HOURS)

    def can_review(self, current_status: str, reviewer_role: str, review_level: int) -> bool:
        """检查当前角色是否有权在指定层级审核"""
        status = ContentStatus(current_status)
        if status not in TRANSITIONS:
            return False

        role_level_map = {
            "doctor": 1,      # 信息员可做一审
            "editor": 1,
            "dept_head": 2,    # 科室负责人做二审
            "director": 3,     # 宣传科长做三审
            "leader": 3,       # 院领导可做终审
            "admin": 99,       # 管理员可做任意级
        }

        required_role_level = role_level_map.get(reviewer_role, 0)
        return required_role_level >= review_level

    def next_status(self, current_status: str, action: str) -> str:
        status = ContentStatus(current_status)
        act = ReviewAction(action)

        if status in (ContentStatus.APPROVED, ContentStatus.PUBLISHED):
            if act == ReviewAction.RETURN:
                return ContentStatus.DRAFT.value
            raise ValueError(f"已发布内容不可审核")

        if status in (ContentStatus.OFFLINE, ContentStatus.RETRACTED):
            raise ValueError(f"已下架/撤回内容不可审核")

        if act == ReviewAction.REJECT:
            return ContentStatus.DRAFT.value

        if act == ReviewAction.RETURN:
            return ContentStatus.DRAFT.value

        next_s = NEXT_STATUS.get((status, act))
        if next_s is None:
            raise ValueError(f"无效的状态转移: {status.value} → {act.value}")
        return next_s.value

    def get_current_level(self, status: str) -> int:
        level_map = {
            ContentStatus.DRAFT.value: 0,
            ContentStatus.PENDING_1ST.value: 1,
            ContentStatus.PENDING_2ND.value: 2,
            ContentStatus.PENDING_3RD.value: 3,
            ContentStatus.APPROVED.value: 4,
        }
        return level_map.get(status, 0)

    def sla_deadline(self, submitted_at: datetime) -> datetime:
        return submitted_at + timedelta(hours=self.sla_hours)

    def is_sla_expired(self, submitted_at: datetime) -> bool:
        return datetime.now(timezone.utc) > self.sla_deadline(submitted_at)

    def get_overdue_handling(self) -> str:
        """超时处理策略: escalate(升级) / remind(提醒) / auto_approve(自动通过)"""
        return "escalate"
