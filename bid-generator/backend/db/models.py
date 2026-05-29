"""
扩展数据模型：用户、订单、订阅、生成记录、提示词模板

兼容 SQLite（开发）和 MySQL（生产），通过 SQLAlchemy 切换
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship

# 复用现有 Base（如果独立运行则创建新的）
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.sqlite import Base

import enum


# ── 枚举类型 ─────────────────────────────────────

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    VIP = "vip"


class MemberLevel(str, enum.Enum):
    FREE = "free"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ENTERPRISE = "enterprise"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class OrderType(str, enum.Enum):
    SUBSCRIPTION = "subscription"    # 订阅套餐
    COUNT_PACK = "count_pack"        # 次数包
    SINGLE_GEN = "single_gen"        # 单次生成


class GenStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# ── 用户表 ───────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    openid = Column(String(128), unique=True, nullable=False, comment="微信 OpenID")
    unionid = Column(String(128), unique=True, nullable=True, comment="微信 UnionID")
    nickname = Column(String(100), comment="微信昵称")
    avatar_url = Column(String(500), comment="头像URL")
    phone = Column(String(20), comment="手机号")
    role = Column(String(20), default=UserRole.USER.value, comment="角色")
    member_level = Column(String(20), default=MemberLevel.FREE.value, comment="会员等级")
    member_expire_at = Column(DateTime, nullable=True, comment="会员到期时间")
    daily_gen_count = Column(Integer, default=0, comment="今日生成次数")
    daily_gen_date = Column(DateTime, nullable=True, comment="生成次数统计日期")
    total_gen_remain = Column(Integer, default=0, comment="剩余总生成次数（次数包）")
    account_balance = Column(Float, default=0.0, comment="账户余额（元）")
    created_at = Column(DateTime, default=datetime.now, comment="注册时间")
    last_login_at = Column(DateTime, default=datetime.now, comment="最后登录时间")
    is_active = Column(Boolean, default=True, comment="是否启用")

    orders = relationship("Order", back_populates="user")
    gen_records = relationship("GenRecord", back_populates="user")


# ── 订阅套餐表 ────────────────────────────────────

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="套餐名称")
    level = Column(String(20), nullable=False, comment="对应会员等级")
    price = Column(Float, nullable=False, comment="价格（元）")
    original_price = Column(Float, comment="原价（元）")
    duration_days = Column(Integer, nullable=False, comment="有效期（天）")
    daily_gen_limit = Column(Integer, default=10, comment="每日生成次数限制")
    total_gen_limit = Column(Integer, default=-1, comment="总生成次数限制，-1表示无限制")
    privileges = Column(JSON, comment="特权说明列表")
    is_active = Column(Boolean, default=True, comment="是否上架")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, default=datetime.now)


# ── 次数包表 ─────────────────────────────────────

class CountPack(Base):
    __tablename__ = "count_packs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="次数包名称")
    count = Column(Integer, nullable=False, comment="生成次数")
    price = Column(Float, nullable=False, comment="价格（元）")
    unit_price = Column(Float, comment="单价（元/次）")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)


# ── 订单表 ────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_no = Column(String(32), unique=True, nullable=False, comment="订单号")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    order_type = Column(String(20), nullable=False, comment="订单类型")
    product_id = Column(Integer, comment="商品ID（套餐或次数包ID）")
    product_name = Column(String(200), comment="商品名称")
    amount = Column(Float, nullable=False, comment="支付金额（元）")
    pay_method = Column(String(20), default="wechat", comment="支付方式")
    pay_transaction_id = Column(String(64), comment="微信支付交易号")
    status = Column(String(20), default=OrderStatus.PENDING.value, comment="订单状态")
    pay_time = Column(DateTime, nullable=True, comment="支付时间")
    expire_time = Column(DateTime, nullable=True, comment="订单过期时间")
    refund_amount = Column(Float, default=0.0, comment="退款金额")
    refund_time = Column(DateTime, nullable=True, comment="退款时间")
    remark = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="orders")


# ── 生成记录表 ────────────────────────────────────

class GenRecord(Base):
    __tablename__ = "gen_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    project_id = Column(Integer, comment="项目ID")
    industry = Column(String(50), comment="行业分类")
    bid_type = Column(String(50), comment="标书类型")
    gen_type = Column(String(20), default="full", comment="生成类型：full/section")
    input_tokens = Column(Integer, default=0, comment="输入 token 数")
    output_tokens = Column(Integer, default=0, comment="输出 token 数")
    cost = Column(Float, default=0.0, comment="成本（元）")
    status = Column(String(20), default=GenStatus.GENERATING.value)
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="gen_records")


# ── 提示词版本表 ──────────────────────────────────

class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="模板名称")
    industry = Column(String(50), comment="行业")
    bid_type = Column(String(50), comment="标书类型")
    version = Column(Integer, default=1, comment="版本号")
    content = Column(JSON, comment="模板内容（完整 YAML 解析后的字典）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    usage_count = Column(Integer, default=0, comment="使用次数")
    avg_score = Column(Float, default=0.0, comment="用户平均评分")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ── 系统配置（保留原有，这里是云端扩展） ──────────

class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置键")
    value = Column(Text, comment="配置值")
    category = Column(String(50), default="general", comment="配置分类")
    description = Column(String(255), comment="说明")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ── 初始化方法 ────────────────────────────────────

def init_extended_tables():
    """在数据库中创建扩展表"""
    from db.sqlite import engine
    Base.metadata.create_all(bind=engine)


def seed_default_plans():
    """初始化默认订阅套餐和次数包"""
    from db.sqlite import SessionLocal
    db = SessionLocal()
    try:
        # 订阅套餐
        existing_plans = db.query(SubscriptionPlan).first()
        if not existing_plans:
            plans = [
                SubscriptionPlan(
                    name="月度会员", level=MemberLevel.MONTHLY.value,
                    price=99.0, original_price=129.0, duration_days=30,
                    daily_gen_limit=10, total_gen_limit=-1,
                    privileges=["全部模板", "高级生成", "Word/PDF导出", "在线编辑"],
                    sort_order=1
                ),
                SubscriptionPlan(
                    name="季度会员", level=MemberLevel.QUARTERLY.value,
                    price=249.0, original_price=297.0, duration_days=90,
                    daily_gen_limit=20, total_gen_limit=-1,
                    privileges=["月度全部特权", "专属客服", "优先生成", "标书审核"],
                    sort_order=2
                ),
                SubscriptionPlan(
                    name="年度会员", level=MemberLevel.YEARLY.value,
                    price=799.0, original_price=1188.0, duration_days=365,
                    daily_gen_limit=50, total_gen_limit=-1,
                    privileges=["季度全部特权", "定制模板", "高级审核", "历史版本管理"],
                    sort_order=3
                ),
                SubscriptionPlan(
                    name="企业版", level=MemberLevel.ENTERPRISE.value,
                    price=2999.0, original_price=3999.0, duration_days=365,
                    daily_gen_limit=-1, total_gen_limit=-1,
                    privileges=["年度全部特权", "多账号管理", "API接口", "专属顾问", "私有知识库"],
                    sort_order=4
                ),
            ]
            db.add_all(plans)

        # 次数包
        existing_packs = db.query(CountPack).first()
        if not existing_packs:
            packs = [
                CountPack(name="单次生成", count=1, price=19.9, unit_price=19.9, sort_order=1),
                CountPack(name="10次卡", count=10, price=149.0, unit_price=14.9, sort_order=2),
                CountPack(name="50次卡", count=50, price=599.0, unit_price=11.98, sort_order=3),
                CountPack(name="100次卡", count=100, price=999.0, unit_price=9.99, sort_order=4),
            ]
            db.add_all(packs)

        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
