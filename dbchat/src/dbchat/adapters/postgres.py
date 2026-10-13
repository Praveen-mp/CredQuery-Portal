from langchain_community.utilities import SQLDatabase

from dbchat.adapters.base import BaseDBAdapter
from dbchat.adapters.registry import register


@register
class PostgresAdapter(BaseDBAdapter):
    key = "postgres"
    display_name = "PostgreSQL"

    def __init__(self, connection: dict):
        uri = (
            f"postgresql+psycopg2://{connection['username']}:{connection['password']}"
            f"@{connection['host']}:{connection['port']}/{connection['database_name']}"
        )
        self._db = SQLDatabase.from_uri(uri)

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

    def run_query(self, query: str) -> str:
        return self._db.run(query)

    @property
    def dialect(self) -> str:
        return self._db.dialect
