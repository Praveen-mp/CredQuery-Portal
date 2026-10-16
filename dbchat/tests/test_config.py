from cryptography.fernet import Fernet

from dbchat.core.config import AppSettings


def _settings(monkeypatch, **env) -> AppSettings:
    monkeypatch.setenv("APP_SECRET_KEY", Fernet.generate_key().decode())
    for key, value in env.items():
        monkeypatch.setenv(key.upper(), str(value))
    return AppSettings()


def test_query_row_limit_and_timeout_have_sane_defaults(monkeypatch):
    settings = _settings(monkeypatch)

    assert settings.query_row_limit == 500
    assert settings.query_timeout_seconds == 10.0


def test_query_row_limit_and_timeout_are_configurable(monkeypatch):
    settings = _settings(monkeypatch, query_row_limit=50, query_timeout_seconds=2.5)

    assert settings.query_row_limit == 50
    assert settings.query_timeout_seconds == 2.5
