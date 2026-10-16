# Contributing

## Dev setup

```bash
uv sync --extra dev
uv run pytest
```

One-time, per clone — install the commit message hook (the repo's `.git` is
at the top level, one level above `dbchat/`, so this is run from there):

```bash
cd ..   # repo root
uv tool install pre-commit   # or: pip install pre-commit / pipx install pre-commit
pre-commit install --hook-type commit-msg
```

## Commit messages

Enforced locally by the hook above, via `.pre-commit-config.yaml` — a commit
with a non-conforming message is rejected before it's created. Format is
[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.

```
feat(reports): add Excel/PDF export for saved reports
fix(adapters): url-encode postgres credentials in the connection URI
docs: document the run_query contract change
```

Since this is a git hook (not version-controlled, not enforced via clone),
anyone contributing needs to run `pre-commit install --hook-type commit-msg`
themselves once — CI should also run `conventional-pre-commit` against the
PR title/commits so an unhooked contributor's push still gets caught.

## CI

Three checks run on every PR touching `dbchat/` (`.github/workflows/`):

- **`tests.yml`** — the full `pytest` suite. No secrets configured or needed:
  every test that touches config/storage sets its own throwaway
  `APP_SECRET_KEY`/`METADATA_DB_PATH` via `monkeypatch`, isolated to a
  per-test temp directory (see `tests/test_api.py`, `tests/test_saved_reports.py`
  for the pattern) — never reuses real credentials, never touches a real
  metadata database.
- **`pylint.yml`** — gated on score (`fail-under = 9.5` in `pyproject.toml`),
  not on "zero messages," so already-reviewed warnings don't block merges.
- **`commit-lint.yml`** — PR title must follow Conventional Commits.

All three run from `dbchat/` so `pyproject.toml`'s `[tool.pylint]` config is
picked up the same way it is locally.

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
           # connection has: host, port, database_name, username, password.
           # Read dbchat.core.config.get_app_settings() here for
           # query_row_limit / query_timeout_seconds and apply the timeout
           # via whatever mechanism your driver supports (e.g. Postgres uses
           # a libpq `options` connect_arg — see adapters/postgres.py).
           ...

       def test_connection(self) -> tuple[bool, str]:
           ...

       def verify_read_only(self) -> tuple[bool | None, str]:
           # Query the connected user's ACTUAL privileges — don't just trust
           # the setup wizard's checkbox. Return False (hard block) if you
           # find real write access (an explicit grant, ownership, admin/
           # superuser status, ...), True if you positively confirmed none,
           # or None if you genuinely can't tell (e.g. your driver/DB has no
           # equivalent of Postgres's information_schema.role_table_grants).
           # See adapters/postgres.py for a worked example and base.py's
           # docstring for exactly what each return value means to callers.
           ...

       def list_tables(self) -> list[str]:
           ...

       def get_schema(self, table_names: list[str]) -> str:
           ...

       def run_query(self, query: str) -> list[dict]:
           # Called with an ALREADY-VALIDATED read-only query — see
           # security/sql_guard.py. Don't re-implement validation here.
           # Return rows as a list of {column: value} dicts, JSON-serializable
           # (convert Decimal/date/UUID/etc. to str), and CAP the row count
           # at self.row_limit — see base.py's docstring for why. Structured
           # rows (not a pre-formatted string) are what let the UI offer
           # Excel/PDF export and "save as report" for free on top of any
           # adapter.
           ...

       @property
       def dialect(self) -> str:
           ...

       @property
       def row_limit(self) -> int:
           # Just return whatever you capped run_query's result at — the
           # agent's system prompt surfaces this so the model writes its own
           # COUNT/LIMIT instead of assuming it saw the whole result set.
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
