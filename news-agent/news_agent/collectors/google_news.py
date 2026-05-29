import re
from datetime import datetime, timezone

import feedparser
import httpx

from news_agent.collectors.base import BaseCollector
from news_agent.utils.logger import logger


class GoogleNewsCollector(BaseCollector):

    FEEDS = {
        "finance": [
            "https://news.google.com/rss/search?q=stock+market+finance+economy&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=wall+street+investing+stocks&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=federal+reserve+interest+rate+inflation&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=crypto+bitcoin+blockchain+defi&hl=en-US&gl=US&ceid=US:en",
        ],
        "ai": [
            "https://news.google.com/rss/search?q=artificial+intelligence+AI+machine+learning&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=openai+deepseek+nvidia+google+AI&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=LLM+GPT+transformer+neural+network&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=AI+agent+robot+autonomous+semiconductor&hl=en-US&gl=US&ceid=US:en",
        ],
        "tech": [
            "https://news.google.com/rss/search?q=technology+startup+innovation+tech&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=chip+data+center+cloud+computing&hl=en-US&gl=US&ceid=US:en",
        ],
        "world": [
            "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB",
            "https://news.google.com/rss/search?q=global+economy+geopolitics+trade&hl=en-US&gl=US&ceid=US:en",
        ],
    }

    def __init__(self):
        super().__init__("google_news")

    def collect(self, max_results: int = 25) -> list[dict]:
        articles: list[dict] = []

        for category, urls in self.FEEDS.items():
            for url in urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:max_results]:
                        articles.append({
                            "url": entry.get("link", ""),
                            "title": entry.get("title", ""),
                            "description": _strip_html(entry.get("summary", "")),
                            "content": _strip_html(entry.get("summary", "")),
                            "publishedAt": _parse_published(entry.get("published", "")),
                            "source": "google_news",
                        })
                    logger.info(f"GoogleNews RSS {category}: {len(feed.entries[:max_results])} fetched")
                except Exception as e:
                    logger.error(f"GoogleNews RSS error ({category}): {e}")

        logger.info(f"GoogleNewsCollector total: {len(articles)} articles")
        return articles


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _parse_published(date_str: str) -> str:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()
