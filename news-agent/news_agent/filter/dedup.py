from datetime import datetime, timezone, timedelta

from news_agent.config import config
from news_agent.filter.fingerprint import compute_simhash, compute_url_hash
from news_agent.storage.models import Article, insert_fingerprint
from news_agent.utils.logger import logger


SIMILARITY_BITS = int((1 - config.pipeline.dedup_similarity_threshold) * 64)


def deduplicate(articles: list[dict]) -> list[dict]:
    """Three-layer dedup pipeline. Returns deduplicated articles."""
    if not articles:
        return []

    logger.info(f"Dedup start: {len(articles)} raw articles")

    articles = _url_dedup(articles)
    logger.info(f"After URL dedup: {len(articles)}")

    articles = _fingerprint_dedup(articles)
    logger.info(f"After fingerprint dedup: {len(articles)}")

    articles = _date_title_dedup(articles)
    logger.info(f"After date+title dedup: {len(articles)}")

    return articles


def _url_dedup(articles: list[dict]) -> list[dict]:
    seen_urls: set[str] = set()
    result = []
    for a in articles:
        url_hash = compute_url_hash(a.get("url", ""))
        if url_hash in seen_urls:
            continue
        if Article.url_exists(a.get("url", "")):
            continue
        seen_urls.add(url_hash)
        result.append(a)
    return result


def _fingerprint_dedup(articles: list[dict]) -> list[dict]:
    result = []
    for a in articles:
        fp = compute_simhash(
            a.get("title", ""),
            a.get("description", "") or a.get("content", ""),
        )
        a["fingerprint"] = fp

        if _is_similar_to_any_in_db(fp):
            logger.debug(f"Skipping similar: {a['title'][:60]}")
            continue
        result.append(a)
    return result


def _is_similar_to_any_in_db(new_fp: str) -> bool:
    from news_agent.storage.database import get_connection

    conn = get_connection()
    rows = conn.execute("SELECT fingerprint FROM fingerprints").fetchall()
    conn.close()

    new_val = int(new_fp, 16)
    for (fp,) in rows:
        if _hamming_distance(new_val, int(fp, 16)) <= SIMILARITY_BITS:
            return True
    return False


def _date_title_dedup(articles: list[dict]) -> list[dict]:
    result = []
    seen_keys = set()
    for a in articles:
        published = a.get("publishedAt", "")[:10]
        title_keywords = _extract_keywords(a.get("title", ""))
        key = (published, tuple(sorted(title_keywords)[:5]))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        result.append(a)
    return result


def _extract_keywords(title: str) -> list[str]:
    import re
    words = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", title.lower())
    stopwords = {"the", "and", "for", "with", "this", "that", "from", "has", "its", "are", "not", "but", "was", "will", "may", "can", "new", "how", "what"}
    return [w for w in words if w not in stopwords]


def _hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def filter_today(articles: list[dict], max_hours: int = 24) -> list[dict]:
    """Remove articles older than max_hours hours from now."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_hours)
    result = []
    for a in articles:
        published = a.get("publishedAt", "")
        if not published:
            result.append(a)
            continue
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if pub_date >= cutoff:
                result.append(a)
            else:
                logger.debug(f"Date filter: too old ({published[:10]}): {a['title'][:50]}")
        except (ValueError, TypeError):
            result.append(a)
    logger.info(f"Date filter (last {max_hours}h): {len(articles)} -> {len(result)}")
    return result


def register_fingerprints(articles: list[dict]) -> None:
    for a in articles:
        if "fingerprint" in a:
            insert_fingerprint(a["fingerprint"], a.get("url", ""))
