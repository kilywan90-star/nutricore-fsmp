import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

from news_agent.collectors.base import BaseCollector
from news_agent.utils.logger import logger


class NewsAPICollector(BaseCollector):

    def __init__(self, api_key: str):
        super().__init__("newsapi")
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"

    def collect(self, max_results: int = 25) -> list[dict]:
        articles: list[dict] = []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        queries = [
            ("everything", {"q": "(finance OR stock OR market OR fed OR economy OR crypto)", "language": "en", "sortBy": "publishedAt", "from": today}),
            ("everything", {"q": "(artificial intelligence OR AI OR machine learning OR deepseek OR openai OR nvidia)", "language": "en", "sortBy": "publishedAt", "from": today}),
        ]

        for endpoint, params in queries:
            params["pageSize"] = min(max_results, 100)
            params["apiKey"] = self.api_key
            try:
                resp = httpx.get(f"{self.base_url}/{endpoint}", params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                if data.get("status") == "ok":
                    for art in data.get("articles", []):
                        articles.append({
                            "url": art.get("url", ""),
                            "title": art.get("title", ""),
                            "description": art.get("description") or "",
                            "content": art.get("content") or "",
                            "publishedAt": art.get("publishedAt", ""),
                            "source": art.get("source", {}).get("name", "newsapi"),
                        })
                logger.info(f"NewsAPI '{params['q'][:40]}': {len(data.get('articles', []))} fetched")
            except Exception as e:
                logger.error(f"NewsAPI query error ({params['q'][:40]}): {e}")

        logger.info(f"NewsAPICollector total: {len(articles)} articles")
        return articles
