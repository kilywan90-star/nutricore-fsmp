"""
用户认证 API
微信登录、JWT 签发、用户信息管理
"""
import os
import hashlib
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from db.sqlite import get_db
from db.models import User, MemberLevel

logger = logging.getLogger(__name__)
router = APIRouter()

# JWT 配置
JWT_SECRET = os.environ.get("JWT_SECRET", "bid-generator-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72

# 微信小程序配置（生产环境从环境变量读取）
WECHAT_APPID = os.environ.get("WECHAT_APPID", "")
WECHAT_SECRET = os.environ.get("WECHAT_SECRET", "")


# ── 请求模型 ──────────────────────────────────────

class WechatLoginRequest(BaseModel):
    code: str
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


class PhoneBindRequest(BaseModel):
    code: str  # 微信手机号组件返回的 code


class UserProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None


# ── JWT 工具 ──────────────────────────────────────

def create_access_token(user_id: int, openid: str) -> str:
    """签发 JWT access token"""
    payload = {
        "user_id": user_id,
        "openid": openid,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """验证并解码 JWT token"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已过期，请重新登录")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Token无效，请重新登录")


def get_current_user(
    authorization: str = Header(..., description="Bearer {token}"),
    db: Session = Depends(get_db)
) -> User:
    """从请求头中解析当前登录用户（作为 FastAPI 依赖项）"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")

    token = authorization[7:]
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    return user


# ── 微信接口调用 ──────────────────────────────────

async def _wx_code2session(code: str) -> dict:
    """调用微信 code2session 接口获取 openid"""
    import httpx

    if not WECHAT_APPID or not WECHAT_SECRET:
        # 开发环境 mock
        logger.warning("微信 AppID/Secret 未配置，使用 mock 数据")
        return {
            "openid": f"dev_openid_{hashlib.md5(code.encode()).hexdigest()[:16]}",
            "session_key": "dev_session_key",
        }

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": WECHAT_APPID,
        "secret": WECHAT_SECRET,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()

        if "errcode" in data and data["errcode"] != 0:
            logger.error(f"微信登录失败: {data}")
            raise HTTPException(status_code=400, detail=f"微信登录失败: {data.get('errmsg', '未知错误')}")

        return {"openid": data["openid"], "session_key": data.get("session_key", "")}


# ── API 路由 ──────────────────────────────────────

@router.post("/login/wechat")
async def wechat_login(req: WechatLoginRequest, db: Session = Depends(get_db)):
    """微信小程序一键登录"""
    # 1. 调用微信接口获取 openid
    wx_data = await _wx_code2session(req.code)
    openid = wx_data["openid"]

    # 2. 查找或创建用户
    user = db.query(User).filter(User.openid == openid).first()
    is_new = False

    if not user:
        user = User(
            openid=openid,
            nickname=req.nickname or f"用户{openid[-8:]}",
            avatar_url=req.avatar_url or "",
            member_level=MemberLevel.FREE.value,
            daily_gen_count=0,
            total_gen_remain=3,  # 新用户赠送 3 次免费生成
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new = True
    else:
        # 更新登录信息
        user.last_login_at = datetime.now()
        if req.nickname:
            user.nickname = req.nickname
        if req.avatar_url:
            user.avatar_url = req.avatar_url
        db.commit()
        db.refresh(user)

    # 3. 签发 JWT
    token = create_access_token(user.id, user.openid)

    return {
        "status": "success",
        "data": {
            "token": token,
            "user_id": user.id,
            "openid": user.openid,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "member_level": user.member_level,
            "member_expire_at": user.member_expire_at.isoformat() if user.member_expire_at else None,
            "daily_gen_count": user.daily_gen_count,
            "daily_gen_limit": _get_daily_limit(user),
            "total_gen_remain": user.total_gen_remain,
            "is_new_user": is_new,
        }
    }


@router.post("/login/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新 JWT token"""
    token = create_access_token(current_user.id, current_user.openid)
    return {"status": "success", "data": {"token": token}}


@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "status": "success",
        "data": {
            "user_id": current_user.id,
            "nickname": current_user.nickname,
            "avatar_url": current_user.avatar_url,
            "phone": current_user.phone,
            "member_level": current_user.member_level,
            "member_expire_at": current_user.member_expire_at.isoformat() if current_user.member_expire_at else None,
            "daily_gen_count": current_user.daily_gen_count,
            "daily_gen_limit": _get_daily_limit(current_user),
            "total_gen_remain": current_user.total_gen_remain,
            "account_balance": current_user.account_balance,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        }
    }


@router.put("/profile")
async def update_profile(
    req: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    if req.nickname:
        current_user.nickname = req.nickname
    if req.avatar_url:
        current_user.avatar_url = req.avatar_url
    db.commit()
    return {"status": "success", "message": "更新成功"}


@router.post("/login/phone")
async def bind_phone(
    req: PhoneBindRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """绑定手机号（通过微信手机号组件）"""
    # 调用微信 getPhoneNumber 接口换取手机号
    # 注：实际实现需要先获取 access_token，然后调用 business endpoint
    # 此处为简化实现，生产环境请参考微信官方文档
    logger.info(f"Phone bind code received for user {current_user.id}")

    # Mock 实现（生产环境需要真实调用微信 API）
    # phone = await _wx_get_phone_number(req.code)
    phone = None  # placeholder

    if phone:
        current_user.phone = phone
        db.commit()

    return {
        "status": "success",
        "message": "手机号绑定功能需要配置微信小程序后启用",
        "data": {"phone": current_user.phone}
    }


# ── 辅助函数 ──────────────────────────────────────

def _get_daily_limit(user: User) -> int:
    """根据会员等级获取每日生成次数上限"""
    limits = {
        MemberLevel.FREE.value: 1,
        MemberLevel.MONTHLY.value: 10,
        MemberLevel.QUARTERLY.value: 20,
        MemberLevel.YEARLY.value: 50,
        MemberLevel.ENTERPRISE.value: -1,  # 无限制
    }
    return limits.get(user.member_level, 1)


def check_gen_quota(user: User, db: Session) -> tuple[bool, str]:
    """
    检查用户生成配额
    返回 (是否允许, 原因说明)
    """
    # 企业版不限制
    if user.member_level == MemberLevel.ENTERPRISE.value:
        return True, ""

    # 检查会员是否过期
    if user.member_level != MemberLevel.FREE.value:
        if user.member_expire_at and user.member_expire_at < datetime.now():
            # 会员过期，降级为免费
            user.member_level = MemberLevel.FREE.value
            user.daily_gen_count = 0
            db.commit()
            # 继续检查免费额度

    # 检查每日限制
    today = datetime.now().date()
    daily_limit = _get_daily_limit(user)

    if daily_limit > 0:  # -1 表示无限制
        if user.daily_gen_date and user.daily_gen_date.date() == today:
            if user.daily_gen_count >= daily_limit:
                return False, f"今日生成次数已用完（{user.daily_gen_count}/{daily_limit}），请明天再试或升级套餐"
        else:
            # 新的一天，重置计数
            user.daily_gen_count = 0
            user.daily_gen_date = datetime.now()
            db.commit()

    # 检查总次数（次数包）
    if user.total_gen_remain <= 0 and user.member_level == MemberLevel.FREE.value:
        return False, "免费生成次数已用完，请购买次数包或订阅会员"

    return True, ""
