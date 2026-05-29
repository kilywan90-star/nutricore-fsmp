import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@dataclass
class DeepSeekConfig:
    api_key: str = field(default_factory=lambda: _env("DEEPSEEK_API_KEY"))
    base_url: str = field(default_factory=lambda: _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
    model: str = field(default_factory=lambda: _env("DEEPSEEK_MODEL", "deepseek-v4-pro"))
    temperature: float = 0.8
    max_tokens: int = 8192


@dataclass
class ArkConfig:
    api_key: str = field(default_factory=lambda: _env("ARK_API_KEY"))
    base_url: str = field(default_factory=lambda: _env("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"))
    model: str = field(default_factory=lambda: _env("SEEDREAM_MODEL", "doubao-seedream-4.5"))


@dataclass
class PipelineConfig:
    newsapi_key: str = field(default_factory=lambda: _env("NEWSAPI_KEY"))
    max_articles_per_run: int = int(_env("MAX_ARTICLES_PER_RUN", "5"))
    max_collect_per_source: int = int(_env("MAX_COLLECT_PER_SOURCE", "50"))
    max_concurrency: int = int(_env("MAX_CONCURRENCY", "8"))
    dedup_similarity_threshold: float = float(_env("DEDUP_SIMILARITY_THRESHOLD", "0.85"))
    fingerprint_ttl_days: int = int(_env("FINGERPRINT_TTL_DAYS", "30"))
    image_size: str = _env("IMAGE_SIZE", "1280x720")
    log_level: str = _env("LOG_LEVEL", "INFO")
    db_path: str = str(ROOT_DIR / "data" / "news_agent.db")
    cache_path: str = str(ROOT_DIR / "data" / "raw_cache.json")
    drafts_dir: str = str(ROOT_DIR / "drafts")
    logs_dir: str = str(ROOT_DIR / "logs")


@dataclass
class Config:
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    ark: ArkConfig = field(default_factory=ArkConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    def validate(self) -> list[str]:
        missing = []
        if not self.deepseek.api_key:
            missing.append("DEEPSEEK_API_KEY")
        if not self.ark.api_key:
            missing.append("ARK_API_KEY")
        if not self.pipeline.newsapi_key:
            missing.append("NEWSAPI_KEY")
        return missing


config = Config()
