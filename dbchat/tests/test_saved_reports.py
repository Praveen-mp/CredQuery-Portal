import pytest
from cryptography.fernet import Fernet

from dbchat.core.config import get_app_settings
from dbchat.storage import store as store_module


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("METADATA_DB_PATH", str(tmp_path / "test_metadata.db"))

    get_app_settings.cache_clear()
    store_module.reset_cache()
    yield store_module
    store_module.reset_cache()
    get_app_settings.cache_clear()


def test_save_list_delete_report_roundtrip(store):
    report_id = store.save_report(
        connection_id=1, name="Weekly signups", question="How many signups last week?"
    )

    reports = store.list_reports(connection_id=1)
    assert len(reports) == 1
    assert reports[0]["id"] == report_id
    assert reports[0]["name"] == "Weekly signups"
    assert reports[0]["question"] == "How many signups last week?"

    other_connection_reports = store.list_reports(connection_id=2)
    assert other_connection_reports == []

    store.delete_report(report_id)
    assert store.list_reports(connection_id=1) == []
