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
        or an equivalent dict of fields being tested before they're saved).

        Note: many underlying clients (e.g. SQLAlchemy's SQLDatabase) connect
        and introspect the schema eagerly, right here in __init__, rather than
        lazily on first use. That means __init__ itself can raise on bad
        host/credentials — every call site that constructs an adapter (the
        setup wizard, the agent builder) MUST wrap construction in try/except,
        not just the call to test_connection()."""

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Attempt to connect right now. Returns (success, message). Called
        from the setup wizard before a connection is saved, so bad credentials
        are caught immediately instead of surfacing as a confusing agent error
        later in a chat session."""

    @abstractmethod
    def verify_read_only(self) -> tuple[bool | None, str]:
        """Queries the connected user's ACTUAL privileges — not the UI
        checkbox self-attestation — and returns:
        - (True, message)  — confirmed no write access.
        - (False, message) — write access was definitively found (e.g. an
          explicit INSERT/UPDATE/DELETE grant, table ownership, or a
          superuser role that bypasses grants entirely). Callers MUST treat
          this as a hard block on saving the connection, not a warning.
        - (None, message)  — couldn't be determined (e.g. the check query
          itself isn't supported, or the user lacks permission to run it).
          Callers should fall back to requiring the user's own confirmation
          in this case, not silently treat it as safe.

        This exists because the DB-level read-only user is the real safety
        boundary (see security/sql_guard.py's docstring) — an honor-system
        checkbox can't actually verify that boundary holds."""

    @abstractmethod
    def list_tables(self) -> list[str]:
        """All table/collection names the connected user can see."""

    @abstractmethod
    def get_schema(self, table_names: list[str]) -> str:
        """Human/LLM-readable schema description for the given tables."""

    @abstractmethod
    def run_query(self, query: str) -> list[dict]:
        """Execute an ALREADY-VALIDATED, read-only query and return the rows
        as a list of {column_name: value} dicts. Callers (the agent's tool
        layer) are responsible for passing the query through
        dbchat.security.sql_guard first — this method does not re-validate,
        it trusts its caller.

        Implementations MUST cap the number of rows returned, using
        `dbchat.core.config.get_app_settings().query_row_limit` (also expose
        it via the `row_limit` property below, consistently — don't hardcode
        a different number) — an unbounded result set is both an
        LLM-context-size problem and a production-database-load problem.
        Implementations should also apply `query_timeout_seconds` from the
        same settings as a server-side statement timeout where the
        underlying driver supports it, so a slow/unindexed query gets
        cancelled instead of hanging the request. Values must be
        JSON-serializable; convert driver-specific types (Decimal, date,
        datetime, UUID, ...) to str/int/float as needed.

        Returning structured rows (not a pre-formatted string) is what lets
        the UI offer Excel/PDF export and "save as report" on top of any
        adapter without adapter-specific code."""

    @property
    @abstractmethod
    def dialect(self) -> str:
        """Dialect/query-language name, surfaced in the agent's system prompt
        so it writes syntactically correct queries (e.g. 'postgresql')."""

    @property
    @abstractmethod
    def row_limit(self) -> int:
        """The cap run_query enforces — surfaced in the agent's system prompt
        so the model knows to write its own LIMIT/aggregation (COUNT, GROUP BY)
        rather than silently relying on results being truncated."""
