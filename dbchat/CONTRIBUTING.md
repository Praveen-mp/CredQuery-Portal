# Contributing

## Dev setup

```bash
uv sync --extra dev
uv run pytest
```

## Adding a new database adapter

This is the main way to contribute. Every adapter implements the same
contract (`src/dbchat/adapters/base.py`), so the agent and UI never need to
change when a new one is added.

1. Create `src/dbchat/adapters/<your_db>.py`:

   ```python
   from dbchat.adapters.base import BaseDBAdapter
   from dbchat.adapters.registry import register

   @register
   class YourDBAdapter(BaseDBAdapter):
       key = "your_db"            # stored as DBConnection.db_type
       display_name = "Your DB"   # shown in the UI dropdown

       def __init__(self, connection: dict):
           # connection has: host, port, database_name, username, password
           ...

       def test_connection(self) -> tuple[bool, str]:
           ...

       def list_tables(self) -> list[str]:
           ...

       def get_schema(self, table_names: list[str]) -> str:
           ...

       def run_query(self, query: str) -> str:
           # Called with an ALREADY-VALIDATED read-only query — see
           # security/sql_guard.py. Don't re-implement validation here.
           ...

       @property
       def dialect(self) -> str:
           ...
   ```

2. Add one line to `src/dbchat/adapters/__init__.py`:

   ```python
   from dbchat.adapters import your_db  # noqa: F401
   ```

3. If your database needs a driver that isn't a core dependency (e.g.
   `pymongo`, `pymysql`), add it as an extra in `pyproject.toml` under
   `[project.optional-dependencies]` rather than a hard dependency, so the
   base install stays light.

4. Add a test in `tests/` following the existing pattern. A live database
   isn't required for most of an adapter's logic — test `test_connection`
   failure handling and anything adapter-specific that doesn't need a real
   connection; integration tests against a real instance are welcome too,
   gated behind an env var so CI doesn't need live credentials.

## Code style

- Keep Streamlit files (`ui/`) UI-only — business logic belongs in
  `agent/`, `adapters/`, `storage/`, or `security/`, not in page files.
- Every adapter's `run_query` must assume it receives untrusted-until-validated
  input from the LLM. Validation is the caller's job (`agent/builder.py`
  passes everything through `security/sql_guard.py` first) — don't duplicate
  or bypass that in an adapter.
- No customer secrets (DB passwords, LLM API keys) in `core/config.py` — that
  file is bootstrap-only, read once at deploy time. Per-connection secrets go
  through `storage/` and are encrypted via `core/crypto.py`.
