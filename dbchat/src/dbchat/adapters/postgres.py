import datetime
import decimal
import uuid
from urllib.parse import quote_plus

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text

from dbchat.adapters.base import BaseDBAdapter
from dbchat.adapters.registry import register
from dbchat.core.config import get_app_settings


def _timeout_connect_args(timeout_seconds: float) -> dict:
    """Builds the libpq connect_args that set a server-side statement_timeout
    (milliseconds) on every connection from the pool. Split out as a pure
    function so the construction logic is testable without a live Postgres
    server — constructing a real PostgresAdapter connects eagerly (see
    adapters/base.py)."""
    timeout_ms = int(timeout_seconds * 1000)
    return {"options": f"-c statement_timeout={timeout_ms}"}


# Three independent signals: an explicit DML grant, table ownership (which
# implies full privileges regardless of explicit grants), and superuser
# status (which bypasses the privilege system entirely). Any one of them
# means this user is NOT actually read-only, whatever the UI checkbox says.
_READ_ONLY_CHECK_QUERY = """
    SELECT
        COALESCE((SELECT rolsuper FROM pg_roles WHERE rolname = current_user), false) AS is_superuser,
        EXISTS (
            SELECT 1 FROM information_schema.role_table_grants
            WHERE grantee = current_user
              AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')
        ) AS has_write_grant,
        EXISTS (
            SELECT 1 FROM pg_tables WHERE tableowner = current_user
        ) AS owns_tables
"""


def _interpret_read_only_check(row: dict) -> tuple[bool, str]:
    """Pure decision logic over the three signals _READ_ONLY_CHECK_QUERY
    returns — split out so it's unit-testable without a live Postgres server."""
    if row["is_superuser"]:
        return False, "This user is a Postgres superuser, which bypasses all privilege checks."
    if row["owns_tables"]:
        return False, (
            "This user owns one or more tables in this database, which grants "
            "implicit full privileges on them regardless of explicit grants."
        )
    if row["has_write_grant"]:
        return False, "This user has INSERT, UPDATE, DELETE, or TRUNCATE privilege on at least one table."
    return True, "No write privileges detected for this user."


def _json_safe(value):
    if isinstance(value, (decimal.Decimal, uuid.UUID)):
        return str(value)
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


@register
class PostgresAdapter(BaseDBAdapter):
    key = "postgres"
    display_name = "PostgreSQL"

    def __init__(self, connection: dict):
        username = quote_plus(connection["username"])
        password = quote_plus(connection["password"])
        uri = (
            f"postgresql+psycopg2://{username}:{password}"
            f"@{connection['host']}:{connection['port']}/{connection['database_name']}"
        )
        # Most managed Postgres (RDS, Cloud SQL, Supabase, ...) requires SSL.
        # sslmode is optional in the connection dict — defaults to "prefer"
        # (use SSL if the server offers it, same as psycopg2's own default).
        sslmode = connection.get("sslmode") or "prefer"
        uri += f"?sslmode={sslmode}"

        settings = get_app_settings()
        self._row_limit = settings.query_row_limit

        # Own the engine ourselves (rather than SQLDatabase.from_uri, which
        # hides it behind a private attribute) so run_query has a supported
        # way to execute raw SQL alongside SQLDatabase's schema introspection.
        # statement_timeout is a libpq/Postgres server-side setting applied to
        # every connection from this pool — a slow/unindexed query gets
        # cancelled by Postgres itself instead of hanging the request.
        self._engine = create_engine(
            uri, connect_args=_timeout_connect_args(settings.query_timeout_seconds)
        )
        self._db = SQLDatabase(self._engine)

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._db.get_usable_table_names()
            return True, "Connected successfully."
        except Exception as exc:
            return False, str(exc)

    def verify_read_only(self) -> tuple[bool | None, str]:
        try:
            with self._engine.connect() as conn:
                row = dict(conn.execute(text(_READ_ONLY_CHECK_QUERY)).mappings().one())
        except Exception as exc:
            return None, f"Could not automatically verify read-only status: {exc}"
        return _interpret_read_only_check(row)

    def list_tables(self) -> list[str]:
        return self._db.get_usable_table_names()

    def get_schema(self, table_names: list[str]) -> str:
        return self._db.get_table_info(table_names=table_names)

    def run_query(self, query: str) -> list[dict]:
        with self._engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = result.fetchmany(self._row_limit)
        return [
            {col: _json_safe(value) for col, value in zip(columns, row)} for row in rows
        ]

    @property
    def dialect(self) -> str:
        return self._db.dialect

    @property
    def row_limit(self) -> int:
        return self._row_limit
