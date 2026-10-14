import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from dbchat.api.app import app
from dbchat.core.config import get_app_settings
from dbchat.storage import store as store_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("METADATA_DB_PATH", str(tmp_path / "test_api_metadata.db"))

    get_app_settings.cache_clear()
    store_module.reset_cache()

    with TestClient(app) as test_client:
        yield test_client

    store_module.reset_cache()
    get_app_settings.cache_clear()


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_connection_create_rejects_unconfirmed_readonly(client):
    response = client.post(
        "/connections",
        json={
            "name": "x", "db_type": "postgres", "host": "h", "port": 5432,
            "database_name": "d", "username": "u", "password": "p",
            "readonly_confirmed": False,
        },
    )
    assert response.status_code == 400


def test_connection_create_list_delete_never_leaks_password(client):
    create = client.post(
        "/connections",
        json={
            "name": "Prod", "db_type": "postgres", "host": "h", "port": 5432,
            "database_name": "d", "username": "u", "password": "super-secret",
            "readonly_confirmed": True,
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert "password" not in body
    connection_id = body["id"]

    listing = client.get("/connections").json()
    assert len(listing) == 1
    assert "password" not in listing[0]

    delete = client.delete(f"/connections/{connection_id}")
    assert delete.status_code == 204
    assert client.get("/connections").json() == []


def test_llm_config_roundtrip_never_leaks_api_key(client):
    assert client.get("/setup/llm-config").json() is None

    put = client.put(
        "/setup/llm-config",
        json={
            "endpoint": "https://example.openai.azure.com",
            "deployment_name": "gpt-4.1-mini",
            "api_version": "2024-12-01-preview",
            "api_key": "super-secret-key",
        },
    )
    assert put.status_code == 204

    get = client.get("/setup/llm-config")
    assert get.status_code == 200
    assert "api_key" not in get.json()
    assert get.json()["deployment_name"] == "gpt-4.1-mini"


def test_report_crud(client):
    connection_id = client.post(
        "/connections",
        json={
            "name": "Prod", "db_type": "postgres", "host": "h", "port": 5432,
            "database_name": "d", "username": "u", "password": "p",
            "readonly_confirmed": True,
        },
    ).json()["id"]

    created = client.post(
        "/reports", json={"connection_id": connection_id, "name": "Row counts", "question": "How many rows?"}
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    listed = client.get(f"/reports?connection_id={connection_id}").json()
    assert len(listed) == 1

    deleted = client.delete(f"/reports/{report_id}")
    assert deleted.status_code == 204
    assert client.get(f"/reports?connection_id={connection_id}").json() == []
