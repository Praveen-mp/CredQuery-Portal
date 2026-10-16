from dbchat.adapters.registry import get_adapter_class
from dbchat.repositories.base import ConnectionRepository


class ConnectionService:
    """Use cases around database connections: test, create, list, delete.
    Depends only on the ConnectionRepository interface and the adapter
    registry — never on storage.store or a concrete adapter class."""

    def __init__(self, connections: ConnectionRepository):
        self._connections = connections

    def test(  # pylint: disable=too-many-arguments, too-many-locals
        # Keyword-only, mapping 1:1 to the connection form/schema fields —
        # same tradeoff as storage.store.save_connection, see its comment.
        # Locals are inherent to the three-way connect/test/verify-read-only
        # branching (see verify_read_only's docstring for the three outcomes),
        # not accidental sprawl.
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
            adapter = adapter_cls(candidate)
        except Exception as exc:  # adapter __init__ may connect eagerly — see adapters/base.py
            return False, str(exc)

        ok, message = adapter.test_connection()
        if not ok:
            return False, message

        # Verify read-only for real instead of trusting the UI checkbox — see
        # BaseDBAdapter.verify_read_only's docstring for what each outcome means.
        read_only, read_only_message = adapter.verify_read_only()
        if read_only is False:
            return False, f"This database user is NOT read-only: {read_only_message}"
        if read_only is None:
            return True, (
                f"Connected successfully. Couldn't automatically confirm read-only "
                f"status ({read_only_message}) — please double-check this manually."
            )
        return True, f"Connected successfully. {read_only_message}"

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
