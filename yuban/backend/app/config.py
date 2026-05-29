import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "渔伴 Yuban API"
    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./yuban.db"

    # Amap
    amap_api_key: str = ""

    # QWeather
    qweather_api_key: str = ""

    # JWT
    jwt_secret_key: str = "yuban-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # Redis (optional for MVP)
    redis_url: str = "redis://localhost:6379/0"

    # WeChat mini-program
    wx_appid: str = ""
    wx_secret: str = ""

    # Membership
    free_trial_days: int = 90

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
