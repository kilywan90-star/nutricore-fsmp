import re

from news_agent.config import config
from news_agent.utils.logger import logger

FINANCE_KEYWORDS = [
    ("stock", 10), ("market", 8), ("fed", 10), ("interest rate", 9),
    ("inflation", 8), ("gdp", 7), ("earnings", 7), ("wall street", 6),
    ("crypto", 6), ("bitcoin", 6), ("nasdaq", 7), ("dow jones", 6),
    ("s&p", 7), ("treasury", 6), ("recession", 9), ("jobs", 5),
]

AI_KEYWORDS = [
    ("artificial intelligence", 10), ("chatgpt", 8), ("openai", 8),
    ("deepseek", 7), ("nvidia", 7), ("gpu", 7), ("machine learning", 7),
    ("large language model", 8), ("llm", 7), ("transformer", 6),
    ("neural network", 6), ("deep learning", 7), ("generative", 7),
    ("claude", 6), ("gemini", 6), ("copilot", 6), ("agent", 5),
    ("robot", 5), ("autonomous", 5), ("semiconductor", 6), ("chip", 6),
    ("data center", 6), ("quantum", 7),
]


def score_and_rank(articles: list[dict]) -> list[dict]:
    """Score articles by relevance to finance/AI, sort, and return top N."""
    for a in articles:
        a["relevance_score"] = _compute_score(a)
        a["category"] = _classify(a)

    scored = sorted(articles, key=lambda a: a.get("relevance_score", 0), reverse=True)

    top_n = config.pipeline.max_articles_per_run
    selected = scored[:top_n]

    logger.info(
        f"Relevance ranking: {len(articles)} scored, top {len(selected)} selected. "
        f"Scores: {[f'{a['title'][:30]}...={a['relevance_score']}' for a in selected]}"
    )
    return selected


def _compute_score(article: dict) -> int:
    title = (article.get("title") or "").lower()
    desc = (article.get("description") or "").lower()
    content = (article.get("content") or "").lower()
    text = f"{title} {desc} {content}"

    score = 0
    for keyword, weight in FINANCE_KEYWORDS + AI_KEYWORDS:
        count = len(re.findall(re.escape(keyword), text, re.IGNORECASE))
        if count > 0:
            score += weight * min(count, 3)

    published = article.get("publishedAt", "")
    if published:
        try:
            from datetime import datetime, timezone, timedelta
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            hours_ago = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
            if hours_ago < 6:
                score += 10
            elif hours_ago < 24:
                score += 5
            elif hours_ago < 48:
                score += 2
        except (ValueError, TypeError):
            pass

    return score


def _classify(article: dict) -> str:
    title = (article.get("title") or "").lower()
    desc = (article.get("description") or "").lower()
    text = f"{title} {desc}"

    finance_score = sum(
        w for kw, w in FINANCE_KEYWORDS if kw in text
    )
    ai_score = sum(
        w for kw, w in AI_KEYWORDS if kw in text
    )

    if ai_score > finance_score:
        return "ai"
    return "finance"
