from dbchat.adapters.registry import get_adapter_class
from dbchat.repositories.base import ConnectionRepository


class ConnectionService:
    """Use cases around database connections: test, create, list, delete.
    Depends only on the ConnectionRepository interface and the adapter
    registry — never on storage.store or a concrete adapter class."""

    def __init__(self, connections: ConnectionRepository):
        self._connections = connections

    def test(  # pylint: disable=too-many-arguments
        # Keyword-only, mapping 1:1 to the connection form/schema fields —
        # same tradeoff as storage.store.save_connection, see its comment.
        self, *, db_type: str, host: str, port: int, database_name: str, username: str, password: str,
        sslmode: str = "prefer",
    ) -> tuple[bool, str]:
        adapter_cls = get_adapter_class(db_type)
        candidate = {
            "host": host,
            "port": port,
            "database_name": database_name,
            "username": username,
            "password": password,
            "sslmode": sslmode,
        }
        try:
            return adapter_cls(candidate).test_connection()
        except Exception as exc:  # adapter __init__ may connect eagerly — see adapters/base.py
            return False, str(exc)

    def create(  # pylint: disable=too-many-arguments
        self, *, name: str, db_type: str, host: str, port: int, database_name: str, username: str,
        password: str, sslmode: str = "prefer", readonly_confirmed: bool,
    ) -> int:
        if not readonly_confirmed:
            raise ValueError("Connection must be confirmed read-only before saving.")
        return self._connections.save(
            name=name,
            db_type=db_type,
            host=host,
            port=port,
            database_name=database_name,
            username=username,
            password=password,
            sslmode=sslmode,
            readonly_confirmed=True,
        )

    def list(self) -> list[dict]:
        return self._connections.list()

    def delete(self, connection_id: int) -> None:
        self._connections.delete(connection_id)
