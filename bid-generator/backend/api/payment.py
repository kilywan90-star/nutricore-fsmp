"""
订单与支付 API
订阅购买、次数包购买、订单管理、支付状态管理
"""
import os
import time
import hashlib
import logging
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from db.sqlite import get_db
from db.models import (
    User, Order, SubscriptionPlan, CountPack,
    OrderStatus, OrderType, MemberLevel,
)
from api.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# 微信支付配置
WECHAT_APPID = os.environ.get("WECHAT_APPID", "")
WECHAT_MCHID = os.environ.get("WECHAT_MCHID", "")
WECHAT_API_KEY = os.environ.get("WECHAT_API_KEY", "")  # API v2 key
WECHAT_API_V3_KEY = os.environ.get("WECHAT_API_V3_KEY", "")  # API v3 key
WECHAT_NOTIFY_URL = os.environ.get("WECHAT_NOTIFY_URL", "https://your-domain.com/api/payment/notify/wechat")

# 生产环境从环境变量读取商户证书路径
WECHAT_CERT_PATH = os.environ.get("WECHAT_CERT_PATH", "")
WECHAT_KEY_PATH = os.environ.get("WECHAT_KEY_PATH", "")


# ── 请求模型 ──────────────────────────────────────

class CreateOrderRequest(BaseModel):
    order_type: str  # subscription / count_pack / single_gen
    product_id: int


class PaymentCallbackData(BaseModel):
    """微信支付回调数据"""
    pass


# ── 工具函数 ──────────────────────────────────────

def _generate_order_no() -> str:
    """生成唯一订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:6].upper()
    return f"BD{timestamp}{rand_str}"


# ── API: 套餐查询 ─────────────────────────────────

@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    """获取所有可购买的订阅套餐"""
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True
    ).order_by(SubscriptionPlan.sort_order).all()

    return {
        "status": "success",
        "data": {
            "subscriptions": [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "original_price": p.original_price,
                    "duration_days": p.duration_days,
                    "daily_gen_limit": p.daily_gen_limit,
                    "privileges": p.privileges,
                }
                for p in plans
            ]
        }
    }


@router.get("/count-packs")
def list_count_packs(db: Session = Depends(get_db)):
    """获取所有次数包"""
    packs = db.query(CountPack).filter(
        CountPack.is_active == True
    ).order_by(CountPack.sort_order).all()

    return {
        "status": "success",
        "data": {
            "count_packs": [
                {
                    "id": p.id,
                    "name": p.name,
                    "count": p.count,
                    "price": p.price,
                    "unit_price": p.unit_price,
                }
                for p in packs
            ]
        }
    }


# ── API: 下单 ─────────────────────────────────────

@router.post("/create-order")
async def create_order(
    req: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建支付订单，返回微信支付参数"""
    order_no = _generate_order_no()

    # 确定商品信息
    if req.order_type == OrderType.SUBSCRIPTION.value:
        product = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == req.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="套餐不存在")
        product_name = product.name
        amount = product.price
    elif req.order_type == OrderType.COUNT_PACK.value:
        product = db.query(CountPack).filter(CountPack.id == req.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="次数包不存在")
        product_name = product.name
        amount = product.price
    elif req.order_type == OrderType.SINGLE_GEN.value:
        product_name = "单次生成"
        amount = 19.9
    else:
        raise HTTPException(status_code=400, detail="无效的订单类型")

    # 创建订单记录
    order = Order(
        order_no=order_no,
        user_id=current_user.id,
        order_type=req.order_type,
        product_id=req.product_id,
        product_name=product_name,
        amount=amount,
        status=OrderStatus.PENDING.value,
        pay_method="wechat",
        expire_time=datetime.now() + timedelta(hours=2),  # 2小时未支付自动取消
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 生成微信支付参数
    pay_params = await _create_wechat_pay_params(
        openid=current_user.openid,
        order_no=order_no,
        amount=amount,
        description=product_name,
    )

    return {
        "status": "success",
        "data": {
            "order_id": order.id,
            "order_no": order_no,
            "amount": amount,
            "product_name": product_name,
            "pay_params": pay_params,  # 小程序调用 wx.requestPayment 的参数
        }
    }


async def _create_wechat_pay_params(openid: str, order_no: str, amount: float, description: str) -> dict:
    """生成微信小程序支付参数"""
    amount_fen = int(amount * 100)  # 元 → 分

    if not WECHAT_MCHID or not WECHAT_API_V3_KEY:
        # 开发环境 mock
        logger.warning("微信支付未配置，返回 mock 支付参数")
        return {
            "timeStamp": str(int(time.time())),
            "nonceStr": hashlib.md5(str(time.time()).encode()).hexdigest()[:16],
            "package": f"prepay_id=mock_prepay_{order_no}",
            "signType": "RSA",
            "paySign": "mock_signature",
            "_mock": True,
            "_note": "请在正式环境配置 WECHAT_MCHID 和 WECHAT_API_V3_KEY",
        }

    # 微信支付 API v3 统一下单
    url = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
    payload = {
        "appid": WECHAT_APPID,
        "mchid": WECHAT_MCHID,
        "description": description,
        "out_trade_no": order_no,
        "notify_url": WECHAT_NOTIFY_URL,
        "amount": {
            "total": amount_fen,
            "currency": "CNY",
        },
        "payer": {
            "openid": openid,
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            data = resp.json()

            if "prepay_id" not in data:
                logger.error(f"微信支付下单失败: {data}")
                raise HTTPException(status_code=500, detail=f"微信支付下单失败: {data.get('message', '未知错误')}")

            prepay_id = data["prepay_id"]

            # 生成小程序调起支付所需的签名参数
            nonce_str = hashlib.md5(str(time.time()).encode()).hexdigest()[:16]
            timestamp = str(int(time.time()))

            sign_str = f"{WECHAT_APPID}\n{timestamp}\n{nonce_str}\nprepay_id={prepay_id}\n"
            # 实际签名需要使用商户私钥，这里简化处理
            pay_sign = "SIGN_NEEDS_CERTIFICATE"

            return {
                "timeStamp": timestamp,
                "nonceStr": nonce_str,
                "package": f"prepay_id={prepay_id}",
                "signType": "RSA",
                "paySign": pay_sign,
            }

    except httpx.TimeoutException:
        raise HTTPException(status_code=500, detail="微信支付接口超时，请重试")


# ── API: 支付回调 ─────────────────────────────────

@router.post("/notify/wechat")
async def wechat_pay_notify(request: dict, db: Session = Depends(get_db)):
    """微信支付回调通知"""
    # 验签（生产环境需要严格实现）
    # 解密 resource 中的数据
    # 更新订单状态

    try:
        # 微信 API v3 回调结构
        event_type = request.get("event_type", "")
        resource = request.get("resource", {})
        ciphertext = resource.get("ciphertext", "")
        # 解密 ciphertext...（生产环境实现 AES-GCM 解密）

        # 简化处理：从回调中提取订单号
        # decrypted_data = _decrypt_wechat_resource(resource)
        # order_no = decrypted_data.get("out_trade_no")
        # transaction_id = decrypted_data.get("transaction_id")

        # Mock: 查找最近创建的待支付订单
        order_no = request.get("out_trade_no", "")
        transaction_id = request.get("transaction_id", "")

        if order_no:
            order = db.query(Order).filter(Order.order_no == order_no).first()
            if order and order.status == OrderStatus.PENDING.value:
                _complete_order(order, transaction_id or "wx_" + order_no, db)

        return {"code": "SUCCESS", "message": "OK"}

    except Exception as e:
        logger.error(f"支付回调处理失败: {e}")
        return {"code": "FAIL", "message": str(e)}


def _complete_order(order: Order, transaction_id: str, db: Session):
    """完成订单：更新订单状态 + 发放权益"""
    order.status = OrderStatus.PAID.value
    order.pay_transaction_id = transaction_id
    order.pay_time = datetime.now()

    user = db.query(User).filter(User.id == order.user_id).first()
    if not user:
        return

    if order.order_type == OrderType.SUBSCRIPTION.value:
        # 订阅：更新会员等级和到期时间
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == order.product_id).first()
        if plan:
            now = datetime.now()
            if user.member_expire_at and user.member_expire_at > now:
                # 续费：在当前到期时间上累加
                user.member_expire_at = user.member_expire_at + timedelta(days=plan.duration_days)
            else:
                user.member_expire_at = now + timedelta(days=plan.duration_days)

            user.member_level = plan.level
            user.daily_gen_count = 0  # 重置每日计数

    elif order.order_type == OrderType.COUNT_PACK.value:
        # 次数包：增加剩余次数
        pack = db.query(CountPack).filter(CountPack.id == order.product_id).first()
        if pack:
            user.total_gen_remain = (user.total_gen_remain or 0) + pack.count

    elif order.order_type == OrderType.SINGLE_GEN.value:
        user.total_gen_remain = (user.total_gen_remain or 0) + 1

    db.commit()


# ── API: 订单管理 ─────────────────────────────────

@router.get("/orders")
def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """用户订单列表"""
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    total = db.query(Order).filter(Order.user_id == current_user.id).count()

    return {
        "status": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "orders": [
                {
                    "id": o.id,
                    "order_no": o.order_no,
                    "order_type": o.order_type,
                    "product_name": o.product_name,
                    "amount": o.amount,
                    "status": o.status,
                    "pay_time": o.pay_time.isoformat() if o.pay_time else None,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ]
        }
    }


@router.get("/orders/{order_id}")
def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """订单详情"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return {
        "status": "success",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "order_type": order.order_type,
            "product_name": order.product_name,
            "amount": order.amount,
            "pay_method": order.pay_method,
            "status": order.status,
            "pay_time": order.pay_time.isoformat() if order.pay_time else None,
            "expire_time": order.expire_time.isoformat() if order.expire_time else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
    }


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """取消未支付的订单"""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != OrderStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="只能取消待支付的订单")

    order.status = OrderStatus.CANCELLED.value
    db.commit()

    return {"status": "success", "message": "订单已取消"}
