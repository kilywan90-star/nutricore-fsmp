import hashlib
import re


def compute_simhash(title: str, content: str) -> str:
    """Compute a 64-bit SimHash fingerprint from title + first 500 chars of content."""
    text = f"{title.strip()} {content.strip()[:500]}"
    text = re.sub(r"\s+", " ", text.lower())
    tokens = _tokenize(text)
    if not tokens:
        return "0" * 16
    hash_value = _simhash_64(tokens)
    return f"{hash_value:016x}"


def compute_url_hash(url: str) -> str:
    """Normalize URL and return MD5."""
    url = re.sub(r"^https?://(www\.)?", "", url.lower()).rstrip("/")
    return hashlib.md5(url.encode()).hexdigest()


def _tokenize(text: str) -> list[str]:
    """Simple 2-gram tokenizer for CJK-aware text."""
    tokens = []
    words = text.split()
    for w in words:
        if len(w) <= 1:
            continue
        for i in range(len(w) - 1):
            tokens.append(w[i:i + 2])
    return tokens if tokens else [text[i:i + 2] for i in range(0, len(text) - 1)]


def _simhash_64(tokens: list[str]) -> int:
    v = [0] * 64
    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest()[:16], 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    result = 0
    for i in range(64):
        if v[i] > 0:
            result |= (1 << i)
    return result
