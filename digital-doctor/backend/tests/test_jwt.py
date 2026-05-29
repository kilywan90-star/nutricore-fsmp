from datetime import datetime, timedelta, timezone
from jose import jwt
from src.security.jwt import create_access_token, create_refresh_token, decode_token
from src.config import settings


def test_create_and_decode_access_token():
    token = create_access_token("user-123", "patient")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "patient"
    assert "exp" in payload


def test_expired_token():
    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": "user-123", "exp": expire}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    try:
        decode_token(token)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "expired" in str(e).lower() or "invalid" in str(e).lower()


def test_invalid_token():
    try:
        decode_token("not.a.valid.token")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid" in str(e)
