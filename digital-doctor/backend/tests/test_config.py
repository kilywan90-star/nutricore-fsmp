import os
from src.config import Settings


def test_settings_load_defaults():
    settings = Settings()
    assert settings.APP_NAME == "digital-doctor"
    assert settings.DEBUG is False


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/db")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    settings = Settings()
    assert "test" in settings.DATABASE_URL
    assert settings.SECRET_KEY == "test-secret"


def test_phi_encryption_key_required_in_production(monkeypatch):
    monkeypatch.setenv("PHI_ENCRYPTION_KEY", "")
    settings = Settings()
    assert settings.PHI_ENCRYPTION_KEY == ""
