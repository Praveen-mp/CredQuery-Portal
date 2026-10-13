from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized, typed application config. Values load from .env once and
    are validated at startup instead of being read ad-hoc with os.environ[...]
    scattered across the codebase."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment_name: str
    azure_openai_api_version: str

    postgres_uri: str

    # Rate limiting: max_requests per window_seconds, per session.
    rate_limit_max_requests: int = 10
    rate_limit_window_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    # lru_cache makes this a process-wide singleton: Settings() parses/validates
    # .env once, not on every call site that needs config.
    return Settings()
