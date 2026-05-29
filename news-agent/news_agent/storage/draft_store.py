import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from news_agent.config import config
from news_agent.storage.models import Article
from news_agent.utils.logger import logger


DRAFTS_DIR = Path(config.pipeline.drafts_dir)
IMAGES_DIR = DRAFTS_DIR / "images"


def save_draft(article: Article) -> Optional[str]:
    """Save article as Markdown draft. Returns the file path."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    date_str = article.collected_at.strftime("%Y%m%d_%H%M%S")
    slug = _slugify(article.title_rewritten or article.title_original)[:40]
    filename = f"{date_str}_{article.category}_{slug}.md"
    filepath = DRAFTS_DIR / filename

    image_ref = ""
    if article.image_path:
        img_name = Path(article.image_path).name
        image_ref = f"![配图](images/{img_name})"

    content = f"""---
category: {article.category}
source: {article.source}
original_url: {article.url}
rewritten_title: {article.title_rewritten or ""}
generated_at: {article.collected_at.isoformat()}
status: {article.status}
---

# {article.title_rewritten or article.title_original}

{image_ref}

{article.body_rewritten or ""}

---

**元数据**

- 原始标题: {article.title_original}
- 来源: {article.source}
- 原始链接: {article.url}
- 分类: {article.category}
"""

    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Draft saved: {filepath.name}")
    return str(filepath)


def list_drafts(limit: int = 20) -> list[Path]:
    """List recent draft files."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [f for f in DRAFTS_DIR.glob("*.md")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    return files[:limit]


def load_draft(filepath: str) -> Optional[str]:
    """Read a draft file."""
    p = Path(filepath)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None


def _slugify(text: str) -> str:
    import re
    text = text.replace(" ", "_")
    text = re.sub(r"[^\w一-鿿_-]", "", text)
    return text[:60]
