"""Content hashing utilities — SHA-256 for tamper-proof audit chain."""
import hashlib
import json


def _canonicalize(value: dict | str) -> bytes:
    """Convert content to canonical bytes for hashing.

    Strings are encoded as UTF-8. Dicts are serialized as sorted JSON (keys sorted)
    to ensure deterministic output for the same logical content regardless of key order.
    """
    if isinstance(value, str):
        return value.encode("utf-8")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


def hash_content(content: dict | str) -> str:
    """SHA-256 hash of canonical JSON or string content.

    Ensures: same logical content always produces the same hash, different content
    always produces different hashes.
    """
    return hashlib.sha256(_canonicalize(content)).hexdigest()


def verify_content_integrity(content: dict | str, stored_hash: str) -> bool:
    """Verify content has not been tampered with since signing.

    Returns True if the current content's hash matches the stored hash.
    """
    return hash_content(content) == stored_hash
