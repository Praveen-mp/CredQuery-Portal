from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Bootstrap, deploy-time-only configuration.

    Everything else — customer database connections, LLM provider credentials —
    is configured through the in-app setup wizard and stored encrypted in the
    metadata database (see dbchat.storage). If you're tempted to add a
    customer secret here, it belongs in storage instead: this file is read
    once at process start by whoever stands up the container, never touched
    by end users of the deployed app.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Root encryption key for everything stored in the metadata DB. Generate one with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Losing this key makes all stored connections/credentials unrecoverable —
    # back it up like you would a database password, not like app config.
    app_secret_key: str

    # Where the app's own metadata (connections, LLM config) is persisted.
    metadata_db_path: str = "dbchat_metadata.db"

    rate_limit_max_requests: int = 10
    rate_limit_window_seconds: float = 60.0


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()
