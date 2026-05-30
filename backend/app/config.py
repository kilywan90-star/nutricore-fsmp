from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fsmp_kb"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    LLM_MODEL: str = "qwen2.5:7b"
    LLM_BASE_URL: str = "http://localhost:11434"

    class Config:
        env_prefix = "FSMP_"


settings = Settings()
