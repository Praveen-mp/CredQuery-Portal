import datetime
import decimal
import uuid
from urllib.parse import quote_plus

from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text

from dbchat.adapters.base import BaseDBAdapter
from dbchat.adapters.registry import register

MAX_ROWS = 500


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
        # Own the engine ourselves (rather than SQLDatabase.from_uri, which
        # hides it behind a private attribute) so run_query has a supported
        # way to execute raw SQL alongside SQLDatabase's schema introspection.
        self._engine = create_engine(uri)
        self._db = SQLDatabase(self._engine)

    def test_connection(self) -> tuple[bool, str]:
        try:
            self._db.get_usable_table_names()
            return True, "Connected successfully."
        except Exception as exc:
            return False, str(exc)

    def list_tables(self) -> list[str]:
        return self._db.get_usable_table_names()

    def get_schema(self, table_names: list[str]) -> str:
        return self._db.get_table_info(table_names=table_names)

    def run_query(self, query: str) -> list[dict]:
        with self._engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = result.fetchmany(MAX_ROWS)
        return [
            {col: _json_safe(value) for col, value in zip(columns, row)} for row in rows
        ]

    @property
    def dialect(self) -> str:
        return self._db.dialect
