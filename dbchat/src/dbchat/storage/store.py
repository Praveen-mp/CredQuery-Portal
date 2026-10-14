from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dbchat.core.config import get_app_settings
from dbchat.core.crypto import decrypt, encrypt
from dbchat.storage.models import Base, DBConnection, LLMConfig, SavedReport


@lru_cache
def _session_factory():
    settings = get_app_settings()
    engine = create_engine(f"sqlite:///{settings.metadata_db_path}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def reset_cache() -> None:
    """Clears the cached engine/sessionmaker. Only needed between tests that
    reconfigure APP_SECRET_KEY/METADATA_DB_PATH — the running app never
    needs to call this."""
    _session_factory.cache_clear()


@contextmanager
def session_scope():
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_connection(  # pylint: disable=too-many-arguments
    # Keyword-only on purpose: this maps 1:1 to the Setup form's fields, and
    # every call site is a keyword call, so there's no ambiguity to trade off
    # against a DTO/dataclass here.
    *,
    name,
    db_type,
    host,
    port,
    database_name,
    username,
    password,
    sslmode="prefer",
    readonly_confirmed=False,
) -> int:
    with session_scope() as session:
        conn = DBConnection(
            name=name,
            db_type=db_type,
            host=host,
            port=port,
            database_name=database_name,
            username=username,
            encrypted_password=encrypt(password),
            sslmode=sslmode,
            readonly_confirmed=readonly_confirmed,
        )
        session.add(conn)
        session.flush()
        return conn.id


def list_connections() -> list[dict]:
    """Returns connection metadata WITHOUT passwords — safe to render in the UI."""
    with session_scope() as session:
        return [
            {
                "id": c.id,
                "name": c.name,
                "db_type": c.db_type,
                "host": c.host,
                "port": c.port,
                "database_name": c.database_name,
                "username": c.username,
                "sslmode": c.sslmode,
                "readonly_confirmed": c.readonly_confirmed,
            }
            for c in session.query(DBConnection).all()
        ]


def get_connection_with_password(connection_id: int) -> dict | None:
    """Only call this where the decrypted password is actually needed
    (building a live DB adapter) — never to display in the UI."""
    with session_scope() as session:
        c = session.get(DBConnection, connection_id)
        if c is None:
            return None
        return {
            "id": c.id,
            "name": c.name,
            "db_type": c.db_type,
            "host": c.host,
            "port": c.port,
            "database_name": c.database_name,
            "username": c.username,
            "password": decrypt(c.encrypted_password),
            "sslmode": c.sslmode,
        }


def delete_connection(connection_id: int) -> None:
    with session_scope() as session:
        c = session.get(DBConnection, connection_id)
        if c is not None:
            session.delete(c)


def save_report(*, connection_id: int, name: str, question: str) -> int:
    with session_scope() as session:
        report = SavedReport(connection_id=connection_id, name=name, question=question)
        session.add(report)
        session.flush()
        return report.id


def list_reports(connection_id: int | None = None) -> list[dict]:
    with session_scope() as session:
        query = session.query(SavedReport)
        if connection_id is not None:
            query = query.filter(SavedReport.connection_id == connection_id)
        return [
            {
                "id": r.id,
                "connection_id": r.connection_id,
                "name": r.name,
                "question": r.question,
                "created_at": r.created_at,
            }
            for r in query.order_by(SavedReport.created_at.desc()).all()
        ]


def get_report(report_id: int) -> dict | None:
    with session_scope() as session:
        r = session.get(SavedReport, report_id)
        if r is None:
            return None
        return {
            "id": r.id,
            "connection_id": r.connection_id,
            "name": r.name,
            "question": r.question,
            "created_at": r.created_at,
        }


def delete_report(report_id: int) -> None:
    with session_scope() as session:
        r = session.get(SavedReport, report_id)
        if r is not None:
            session.delete(r)


def save_llm_config(*, provider, endpoint, deployment_name, api_version, api_key) -> None:
    with session_scope() as session:
        existing = session.query(LLMConfig).first()
        if existing is not None:
            existing.provider = provider
            existing.endpoint = endpoint
            existing.deployment_name = deployment_name
            existing.api_version = api_version
            existing.encrypted_api_key = encrypt(api_key)
        else:
            session.add(
                LLMConfig(
                    provider=provider,
                    endpoint=endpoint,
                    deployment_name=deployment_name,
                    api_version=api_version,
                    encrypted_api_key=encrypt(api_key),
                )
            )


def get_llm_config() -> dict | None:
    with session_scope() as session:
        c = session.query(LLMConfig).first()
        if c is None:
            return None
        return {
            "provider": c.provider,
            "endpoint": c.endpoint,
            "deployment_name": c.deployment_name,
            "api_version": c.api_version,
            "api_key": decrypt(c.encrypted_api_key),
        }
