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

    # Grassroots / offline deployment
    DEPLOYMENT_MODE: str = "standard"  # standard | grassroots
    OFFLINE_MODE_ENABLED: bool = False
    SYNC_INTERVAL_MINUTES: int = 30

    # EMR Adapter
    EMR_VENDOR: str = "noop"  # noop | neusoft | winning | bsoft | wonders | xintong | zuobiao | fhir
    EMR_ENDPOINT: str = ""
    EMR_AUTH_TYPE: str = "basic"  # basic | token | cert | none
    EMR_AUTH_USERNAME: str = ""
    EMR_AUTH_PASSWORD: str = ""
    EMR_TIMEOUT_SECONDS: int = 30
    EMR_RETRY_COUNT: int = 2

    # Critical Alert Closed-Loop
    CRITICAL_ALERT_ENABLED: bool = True
    CLOSED_LOOP_MODE: str = "lightweight"  # lightweight | standard | complete
    LIGHTWEIGHT_ACK_TIMEOUT_MINUTES: int = 30
    LIGHTWEIGHT_ESCALATE_TO_ROLE: str = "department_head"
    LIGHTWEIGHT_ESCALATE_AFTER_MINUTES: int = 60
    STANDARD_LIS_ENDPOINT: str = ""
    STANDARD_NURSE_STATION_NOTIFY: bool = True
    STANDARD_DUAL_CONFIRM_REQUIRED: bool = True
    COMPLETE_PATIENT_SMS_ENABLED: bool = True
    COMPLETE_PATIENT_PHONE_ENABLED: bool = False
    COMPLETE_EMERGENCY_NAVIGATION_ENABLED: bool = True

    # Critical alert closed-loop system
    CRITICAL_ALERT_ENABLED: bool = True
    CLOSED_LOOP_MODE: str = "lightweight"  # lightweight | standard | complete

    # Lightweight mode
    LIGHTWEIGHT_ACK_TIMEOUT_MINUTES: int = 30
    LIGHTWEIGHT_ESCALATE_TO_ROLE: str = "department_head"
    LIGHTWEIGHT_ESCALATE_AFTER_MINUTES: int = 60

    # Standard mode (needs LIS integration)
    STANDARD_LIS_ENDPOINT: str = ""
    STANDARD_NURSE_STATION_NOTIFY: bool = True
    STANDARD_DUAL_CONFIRM_REQUIRED: bool = True

    # Complete mode (needs patient app)
    COMPLETE_PATIENT_SMS_ENABLED: bool = True
    COMPLETE_PATIENT_PHONE_ENABLED: bool = False
    COMPLETE_EMERGENCY_NAVIGATION_ENABLED: bool = True

    model_config = {"env_prefix": "", "case_sensitive": True}


settings = Settings()
