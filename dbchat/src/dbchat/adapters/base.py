from abc import ABC, abstractmethod


class BaseDBAdapter(ABC):
    """Contract every database adapter must implement.

    To add support for a new database (MySQL, MongoDB, Snowflake, BigQuery, ...):
    1. Subclass BaseDBAdapter and implement every method below.
    2. Decorate it with @register from dbchat.adapters.registry.
    3. Import your new module in dbchat/adapters/__init__.py so the
       decorator actually runs and the adapter becomes selectable in the UI.

    Nothing in the agent layer or the UI needs to know which concrete
    database it's talking to — they only ever call this interface.
    """

    #: short machine-readable key, e.g. "postgres" — stored as DBConnection.db_type
    key: str
    #: human-readable name shown in the UI's connection-type dropdown
    display_name: str

    @abstractmethod
    def __init__(self, connection: dict):
        """`connection` has keys: host, port, database_name, username, password
        (the decrypted dict returned by storage.store.get_connection_with_password,
        or an equivalent dict of fields being tested before they're saved)."""

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Attempt to connect right now. Returns (success, message). Called
        from the setup wizard before a connection is saved, so bad credentials
        are caught immediately instead of surfacing as a confusing agent error
        later in a chat session."""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """All table/collection names the connected user can see."""

    @abstractmethod
    def get_schema(self, table_names: list[str]) -> str:
        """Human/LLM-readable schema description for the given tables."""

    @abstractmethod
    def run_query(self, query: str) -> str:
        """Execute an ALREADY-VALIDATED, read-only query and return a string
        representation of the result. Callers (the agent's tool layer) are
        responsible for passing the query through dbchat.security.sql_guard
        first — this method does not re-validate, it trusts its caller."""

    @property
    @abstractmethod
    def dialect(self) -> str:
        """Dialect/query-language name, surfaced in the agent's system prompt
        so it writes syntactically correct queries (e.g. 'postgresql')."""
