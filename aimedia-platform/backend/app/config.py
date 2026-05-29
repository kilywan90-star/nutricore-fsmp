from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── 数据库 (开发默认 SQLite，生产用 PostgreSQL) ──
    database_url: str = "sqlite+aiosqlite:///./aimedia.db"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM ──
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096

    # ── JWT ──
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # ── 文件存储 ──
    storage_dir: str = "./storage"
    max_upload_size_mb: int = 500

    # ── 钉钉 ──
    dingtalk_app_key: str = ""
    dingtalk_app_secret: str = ""
    dingtalk_agent_id: str = ""

    # ── 环境 ──
    env: str = "development"
    log_level: str = "DEBUG"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
