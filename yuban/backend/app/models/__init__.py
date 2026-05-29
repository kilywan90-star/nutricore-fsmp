"""SQLAlchemy 数据库模型"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, Enum, JSON, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class SpotType(str, enum.Enum):
    HEI_KENG = "黑坑"
    YE_DIAO = "野钓"
    SHUI_KU = "水库"
    HAI_DIAO = "海钓"
    XI_LIU = "溪流"
    LU_YA = "路亚基地"
    QI_TA = "其他"


class PostType(str, enum.Enum):
    YU_HUO = "鱼获"
    FENG_JING = "风景"
    JING_YAN = "经验"
    QIU_ZHU = "求助"


class YuediaoStatus(str, enum.Enum):
    RECRUITING = "招募中"
    FULL = "已满"
    ENDED = "已结束"
    CANCELLED = "已取消"


class CompanionType(str, enum.Enum):
    DIAO_DAO = "钓导"
    PEI_DIAO = "陪钓"
    SHE_YING = "摄影"
    QI_TA = "其他"


class OrderStatus(str, enum.Enum):
    PENDING = "待确认"
    CONFIRMED = "已确认"
    ONGOING = "进行中"
    COMPLETED = "已完成"
    CANCELLED = "已取消"
    REFUNDED = "已退款"


class Spot(Base):
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    address = Column(String(500))
    province = Column(String(50))
    city = Column(String(50), index=True)
    district = Column(String(50))
    type = Column(Enum(SpotType), default=SpotType.QI_TA, index=True)
    fish_species = Column(JSON, default=list)
    price_info = Column(JSON, default=dict)
    water_depth = Column(String(50))
    water_quality = Column(String(50))
    facilities = Column(JSON, default=dict)
    photos = Column(JSON, default=list)
    tips = Column(Text)
    rating = Column(Float, default=0.0)
    crowd_level = Column(Integer, default=0)  # 0-5 拥挤程度
    source = Column(String(50), default="高德地图")
    amap_id = Column(String(50))
    tel = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    openid = Column(String(100), unique=True, nullable=False, index=True)
    nickname = Column(String(100))
    avatar = Column(String(500))
    level = Column(Integer, default=1)
    total_catches = Column(Integer, default=0)
    max_record = Column(Float, default=0.0)  # 最大鱼获重量(斤)
    favorite_methods = Column(JSON, default=list)
    is_member = Column(Boolean, default=False)
    member_expire_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("spots.id"), index=True)
    type = Column(Enum(PostType), default=PostType.YU_HUO)
    content = Column(Text)
    images = Column(JSON, default=list)
    fish_info = Column(JSON, default=dict)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    lat = Column(Float)
    lng = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", lazy="joined")
    spot = relationship("Spot", lazy="joined")


class YuediaoSession(Base):
    __tablename__ = "yuediao_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("spots.id"))
    target_date = Column(DateTime, nullable=False)
    max_participants = Column(Integer, default=2)
    current_count = Column(Integer, default=1)
    requirements = Column(Text)
    status = Column(Enum(YuediaoStatus), default=YuediaoStatus.RECRUITING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", lazy="joined")
    spot = relationship("Spot", lazy="joined")


class Companion(Base):
    __tablename__ = "companions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(Enum(CompanionType), default=CompanionType.PEI_DIAO)
    price_per_hour = Column(Float, default=0.0)
    services = Column(JSON, default=list)
    rating = Column(Float, default=5.0)
    order_count = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    bio = Column(Text)
    photos = Column(JSON, default=list)
    available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", lazy="joined")


class CompanionOrder(Base):
    __tablename__ = "companion_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    companion_id = Column(Integer, ForeignKey("companions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    spot_id = Column(Integer, ForeignKey("spots.id"))
    service_date = Column(DateTime, nullable=False)
    duration = Column(Float, default=2.0)  # 小时
    total_price = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    rating = Column(Float)
    review = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    companion = relationship("Companion", lazy="joined")
    user = relationship("User", lazy="joined")
    spot = relationship("Spot", lazy="joined")
