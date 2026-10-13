from functools import lru_cache

from langchain_community.utilities import SQLDatabase

from core.config import get_settings


@lru_cache
def get_postgres_db() -> SQLDatabase:
    # lru_cache: one SQLAlchemy engine/connection pool per process, reused
    # across every call instead of reconnecting per request.
    settings = get_settings()
    return SQLDatabase.from_uri(settings.postgres_uri)
