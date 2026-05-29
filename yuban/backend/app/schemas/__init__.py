"""Pydantic schemas - API 请求/响应模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ========== 钓点 ==========
class SpotListQuery(BaseModel):
    lat: Optional[float] = Field(None, description="用户纬度")
    lng: Optional[float] = Field(None, description="用户经度")
    city: Optional[str] = None
    type: Optional[str] = None
    keyword: Optional[str] = None
    radius: int = Field(50000, description="搜索半径(米)")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    sort_by: str = Field("distance", description="排序方式: distance/rating/fishing_index")


class SpotOut(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    address: Optional[str]
    province: Optional[str]
    city: Optional[str]
    district: Optional[str]
    type: Optional[str]
    fish_species: Optional[list] = []
    price_info: Optional[dict] = {}
    water_depth: Optional[str]
    water_quality: Optional[str]
    facilities: Optional[dict] = {}
    photos: Optional[list] = []
    tips: Optional[str]
    rating: Optional[float]
    crowd_level: Optional[int]
    source: Optional[str]
    tel: Optional[str]
    distance: Optional[float] = None  # 距用户距离(米)
    fishing_index: Optional[dict] = None  # 钓鱼指数

    model_config = {"from_attributes": True}


class SpotDetailOut(SpotOut):
    today_index: Optional[dict] = None
    weather: Optional[dict] = None
    recent_posts: Optional[list] = []
    nearby_spots: Optional[list] = []


# ========== 钓鱼指数 ==========
class FishingIndexOut(BaseModel):
    score: int = Field(..., ge=0, le=100, description="综合钓鱼指数")
    summary: str = Field(..., description="一句话建议")
    details: dict = Field(default_factory=dict)
    gear_recommendations: list = Field(default_factory=list, description="装备推荐")
    insect_level: int = Field(default=0, ge=0, le=5, description="蚊虫活跃等级")


class WeatherOut(BaseModel):
    temp: float
    feels_like: float
    humidity: float
    wind_speed: float
    wind_direction: str
    pressure: float
    weather_desc: str
    precipitation_prob: float
    uv_index: float
    hourly: list = []
    sunrise: str
    sunset: str


# ========== 社区 ==========
class PostCreate(BaseModel):
    spot_id: Optional[int] = None
    type: str = "鱼获"
    content: str
    images: list = []
    fish_info: dict = {}
    lat: Optional[float] = None
    lng: Optional[float] = None


class PostOut(BaseModel):
    id: int
    user_id: int
    spot_id: Optional[int]
    type: str
    content: str
    images: list
    fish_info: dict
    likes_count: int
    comments_count: int
    created_at: datetime
    user: Optional[dict] = None
    spot: Optional[dict] = None

    model_config = {"from_attributes": True}


# ========== 约钓 ==========
class YuediaoCreate(BaseModel):
    spot_id: int
    target_date: datetime
    max_participants: int = 2
    requirements: str = ""


class YuediaoOut(BaseModel):
    id: int
    creator_id: int
    spot_id: Optional[int]
    target_date: datetime
    max_participants: int
    current_count: int
    requirements: str
    status: str
    created_at: datetime
    creator: Optional[dict] = None
    spot: Optional[dict] = None

    model_config = {"from_attributes": True}


# ========== 陪钓 ==========
class CompanionCreate(BaseModel):
    type: str = "陪钓"
    price_per_hour: float
    services: list = []
    bio: str = ""
    photos: list = []


class CompanionOut(BaseModel):
    id: int
    user_id: int
    type: str
    price_per_hour: float
    services: list
    rating: float
    order_count: int
    verified: bool
    bio: str
    photos: list
    user: Optional[dict] = None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    companion_id: int
    spot_id: int
    service_date: datetime
    duration: float = 2.0


class OrderOut(BaseModel):
    id: int
    companion_id: int
    user_id: int
    spot_id: Optional[int]
    service_date: datetime
    duration: float
    total_price: float
    status: str
    rating: Optional[float]
    review: Optional[str]
    created_at: datetime
    companion: Optional[dict] = None
    spot: Optional[dict] = None

    model_config = {"from_attributes": True}


# ========== 用户 ==========
class UserProfile(BaseModel):
    id: int
    nickname: str
    avatar: Optional[str]
    level: int
    total_catches: int
    max_record: float
    favorite_methods: list
    is_member: bool
    member_expire_at: Optional[datetime]

    model_config = {"from_attributes": True}
