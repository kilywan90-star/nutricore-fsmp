import base64
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from openai import OpenAI

from news_agent.config import config
from news_agent.utils.logger import logger


class SeedreamClient:

    def __init__(self):
        self.client = OpenAI(
            api_key=config.ark.api_key,
            base_url=config.ark.base_url,
        )
        self.output_dir = Path(config.pipeline.drafts_dir) / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, title: str, category: str) -> Optional[str]:
        """Generate an AI image for the article. Returns file path or None."""
        prompt = _build_image_prompt(title, category)

        for attempt in range(2):
            try:
                response = self.client.images.generate(
                    model=config.ark.model,
                    prompt=prompt,
                    size=config.pipeline.image_size,
                    response_format="b64_json",
                    extra_body={"watermark": False},
                )

                b64_data = response.data[0].b64_json
                if not b64_data:
                    logger.error("Seedream returned empty image data")
                    continue

                image_bytes = base64.b64decode(b64_data)
                filename = f"{_hash_title(title)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                filepath = self.output_dir / filename
                filepath.write_bytes(image_bytes)
                logger.info(f"Image generated: {filepath.name} ({len(image_bytes)} bytes)")
                return str(filepath)

            except Exception as e:
                logger.error(f"Seedream API error (attempt {attempt + 1}): {e}")

        return None


def _build_image_prompt(title: str, category: str) -> str:
    """Extract visual elements from title and build a Seedream-optimized prompt."""
    title_clean = re.sub(r"[^一-鿿㐀-䶿a-zA-Z0-9\s]", " ", title)
    keywords = _extract_visual_keywords(title_clean)
    category_style = "financial chart, professional tone, data visualization" if category == "finance" else "futuristic technology, AI neural networks, modern computing"
    prompt = (
        f"Professional editorial illustration, news article header image. "
        f"Subject: {', '.join(keywords) if keywords else title_clean[:100]}. "
        f"Style: {category_style}. "
        f"High quality, 4K, clean composition, suitable for news media, "
        f"no text overlay, no watermark, photorealistic."
    )
    logger.debug(f"Image prompt: {prompt[:200]}")
    return prompt


def _extract_visual_keywords(text: str) -> list[str]:
    entities = re.findall(r"[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)?", text)
    chinese_entities = re.findall(r"[一-鿿㐀-䶿]{2,6}", text)
    visual_words = [w for w in entities + chinese_entities if w.lower() not in {"the", "and", "for", "with", "this", "that", "from", "has", "its", "will", "may"}]
    return visual_words[:5]


def _hash_title(title: str) -> str:
    return hashlib.md5(title.encode()).hexdigest()[:12]
