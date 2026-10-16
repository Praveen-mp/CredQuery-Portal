import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from dbchat.api.app import app
from dbchat.core.config import get_app_settings
from dbchat.storage import store as store_module


@pytest.fixture
def client_factory(tmp_path, monkeypatch):
    """Unlike test_api.py's `client` fixture, this one lets each test set
    API_KEY before the client is constructed (app startup reads settings)."""

    def _make(api_key: str | None = None):
        monkeypatch.setenv("APP_SECRET_KEY", Fernet.generate_key().decode())
        monkeypatch.setenv("METADATA_DB_PATH", str(tmp_path / "test_auth_metadata.db"))
        if api_key is not None:
            monkeypatch.setenv("API_KEY", api_key)
        get_app_settings.cache_clear()
        store_module.reset_cache()
        return TestClient(app)

    yield _make

    store_module.reset_cache()
    get_app_settings.cache_clear()


def test_api_open_by_default_when_no_api_key_configured(client_factory):
    client = client_factory(api_key=None)

    assert client.get("/connections").status_code == 200


def test_api_rejects_missing_authorization_header_when_key_configured(client_factory):
    client = client_factory(api_key="secret-token")

    response = client.get("/connections")

    assert response.status_code == 401


def test_api_rejects_wrong_token(client_factory):
    client = client_factory(api_key="secret-token")

    response = client.get("/connections", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401


def test_api_accepts_correct_bearer_token(client_factory):
    client = client_factory(api_key="secret-token")

    response = client.get("/connections", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200


def test_health_never_requires_a_token(client_factory):
    client = client_factory(api_key="secret-token")

    response = client.get("/health")

    assert response.status_code == 200
