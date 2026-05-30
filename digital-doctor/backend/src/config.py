# digital-doctor/backend/src/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "digital-doctor"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://ddd:ddd_secret_dev@localhost:5432/digital_doctor"
    REDIS_URL: str = "redis://localhost:6379/0"

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.3
    LLM_RETRY_COUNT: int = 3
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_FALLBACK_ENABLED: bool = True

    SECRET_KEY: str = "dev-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    PHI_ENCRYPTION_KEY: str = ""

    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_STORAGE_TYPE: str = "local"
    BACKUP_S3_BUCKET: str = ""
    BACKUP_S3_ENDPOINT: str = ""
    BACKUP_ENCRYPTION_ENABLED: bool = True

    # Production
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    LOG_LEVEL: str = "INFO"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # WeChat
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""

    # Celery / Notifications
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    SMS_PROVIDER: str = "mock"
    NOTIFICATION_CLEANUP_DAYS: int = 90

    model_config = {"env_prefix": "", "case_sensitive": True}


settings = Settings()
