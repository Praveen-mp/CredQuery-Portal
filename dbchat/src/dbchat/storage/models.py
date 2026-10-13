import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DBConnection(Base):
    """One saved, end-user-configured database connection. `encrypted_password`
    is never stored or returned in plaintext outside of storage.store."""

    __tablename__ = "db_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    db_type: Mapped[str] = mapped_column(String)  # matches an adapters.registry key, e.g. "postgres"
    host: Mapped[str] = mapped_column(String)
    port: Mapped[int] = mapped_column(Integer)
    database_name: Mapped[str] = mapped_column(String)
    username: Mapped[str] = mapped_column(String)
    encrypted_password: Mapped[str] = mapped_column(String)
    readonly_confirmed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())


class LLMConfig(Base):
    """Singleton-ish table (one active row) for the deployment's LLM provider
    credentials, set via the setup wizard."""

    __tablename__ = "llm_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String, default="azure_openai")
    endpoint: Mapped[str] = mapped_column(String)
    deployment_name: Mapped[str] = mapped_column(String)
    api_version: Mapped[str] = mapped_column(String)
    encrypted_api_key: Mapped[str] = mapped_column(String)
