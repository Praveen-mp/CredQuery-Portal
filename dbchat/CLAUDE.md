# dbchat — engineering guide

This file governs how code gets written in this repo, especially the FastAPI
backend (`src/dbchat/api/`). Read it before adding a route, service, or
dependency.

## Context

`dbchat` already has a working core: `adapters/` (DB plugin interface),
`agent/` (LangChain agent builder), `storage/` (encrypted metadata store),
`security/` (SQL guard + rate limiter), `reports/` (export). `ui/` is a
Streamlit frontend over that core. The FastAPI backend is a **second,
independent frontend over the same core** — not a rewrite of it. If you find
yourself duplicating logic that already exists in `agent/`, `adapters/`, or
`storage/`, stop: import and reuse it instead. The API exists so other
clients (a future web frontend, a Slack bot, a CLI) can reach the same engine
Streamlit already uses.

## Layered architecture — know which layer you're in

```
api/routers/     → HTTP only: parse request, call a service, return a response.
                   No SQL, no LangChain, no adapter construction here.
api/schemas/     → Pydantic request/response models. Never reuse these as
                   internal domain objects — they're a wire format.
api/services/    → Business logic. Orchestrates repositories + adapters +
                   the agent layer. This is where a "use case" lives
                   (e.g. "run a saved report," "test a new connection").
api/deps.py      → FastAPI `Depends()` providers. The ONLY place that wires
                   concrete implementations to abstract interfaces.
storage/         → Already exists. Repositories wrap this, they don't
                   replace it — don't reimplement connection CRUD here.
adapters/        → Already exists (BaseDBAdapter + registry). Services depend
                   on the ABSTRACT BaseDBAdapter type, never import
                   PostgresAdapter directly outside adapters/registry.py.
agent/           → Already exists. Services call build_agent_for_connection,
                   they don't construct LangChain tools/agents themselves.
```

A router that imports `sqlalchemy`, `psycopg2`, or `langchain` directly is a
sign something's in the wrong layer.

## OOP patterns to actually use here

**Repository pattern** for anything touching `storage/`. Don't call
`storage.store.save_connection(...)` from a router or service directly —
wrap it in a class implementing a small interface, so a service depends on
the interface, not on SQLite-via-SQLAlchemy specifics:

```python
class ConnectionRepository(ABC):
    @abstractmethod
    def save(self, connection: ConnectionCreate) -> int: ...
    @abstractmethod
    def list(self) -> list[ConnectionSummary]: ...
    @abstractmethod
    def get_with_credentials(self, connection_id: int) -> ConnectionCredentials | None: ...

class SqliteConnectionRepository(ConnectionRepository):
    # thin wrapper around dbchat.storage.store
    ...
```

Why: `storage/store.py`'s module-level functions are fine for Streamlit
(single-process, no need to mock). An API with tests needs to substitute a
fake repository without spinning up SQLite — that's the whole point of the
interface.

**Service layer** for business logic, one class per bounded concern
(`ConnectionService`, `ReportService`, `ChatService`). A service takes its
dependencies (repository, adapter factory) through `__init__`, never imports
them as module-level globals:

```python
class ReportService:
    def __init__(self, reports: ReportRepository, agent_factory: AgentFactory):
        self._reports = reports
        self._agent_factory = agent_factory

    def run(self, report_id: int) -> ReportResult:
        report = self._reports.get(report_id)
        agent = self._agent_factory.build(report.connection_id)
        ...
```

**Dependency inversion, concretely**: `BaseDBAdapter` already exists for
this — a service that needs to run a query depends on `BaseDBAdapter`, and
`adapters.registry.get_adapter_class` is the one place that resolves a
concrete class. Don't add a second way to go from `db_type` string to a
class; don't `isinstance`-check for `PostgresAdapter` in a service — if
behavior needs to differ per database type, that's a method on the adapter,
not a branch in the service.

**Dependency injection via FastAPI `Depends`**, defined once in `api/deps.py`:

```python
def get_connection_repository() -> ConnectionRepository:
    return SqliteConnectionRepository()

def get_report_service(
    repo: ConnectionRepository = Depends(get_connection_repository),
) -> ReportService:
    return ReportService(repo, AgentFactory())
```

Routers only ever see the abstract type as a parameter annotation. This is
what makes a route testable with `app.dependency_overrides[...]` instead of
monkeypatching imports.

## Naming conventions

| What | Convention | Example |
|---|---|---|
| Module | `snake_case`, singular noun | `connection_service.py` |
| Class | `PascalCase`, named for its role | `ConnectionRepository`, `ReportService` |
| Abstract base | `Base` prefix (matches `BaseDBAdapter`) | `BaseRepository` |
| Pydantic request schema | `<Noun>Create` / `<Noun>Update` | `ConnectionCreate` |
| Pydantic response schema | `<Noun>` or `<Noun>Summary`/`<Noun>Detail` | `ConnectionSummary` |
| FastAPI router variable | `router` (file scoped, one per domain file) | `api/routers/connections.py` |
| Route function | verb-first, matches HTTP intent | `create_connection`, `list_reports` |
| Dependency provider | `get_<thing>` | `get_report_service` |
| Private/internal helper | leading underscore | `_build_uri` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_ROWS` (already the pattern in `adapters/postgres.py`) |

No Hungarian notation, no `I` prefix on interfaces (`ConnectionRepository`,
not `IConnectionRepository`) — Python convention is the ABC name itself
signals the contract.

## Loose coupling checklist (apply before opening a PR)

- Does a router import anything from `sqlalchemy`, `psycopg2`, or
  `langchain_*` directly? If yes, that logic belongs in a service/repository.
- Does a service construct a concrete repository/adapter itself (`= SqliteConnectionRepository()`
  inline), instead of receiving it as a constructor argument? If yes, it's
  not actually swappable — fix the constructor.
- Could you unit-test this service with a hand-written fake repository, with
  zero database or HTTP involved? If no, something is too tightly coupled.
- Did you add a new way to map `db_type` → adapter class instead of using
  `adapters.registry`? Don't.

## Existing conventions to keep (already correct, don't "fix")

- `security/sql_guard.py` and `security/rate_limiter.py` are pure, dependency-free
  modules — keep them that way; don't make them depend on FastAPI or the ORM.
- Adapters never re-validate SQL themselves (`run_query` trusts its caller) —
  the guard runs once, in the agent/service layer, not duplicated per adapter.
- Secrets (DB passwords, LLM API keys) are encrypted via `core/crypto.py` and
  never logged or returned in a response schema — a `ConnectionSummary`
  response model must never include a password field, even encrypted.
- Broad `except Exception` at adapter/agent boundaries is intentional (see
  `adapters/base.py` docstring) — don't narrow it "for cleanliness."

## Testing

Every service and repository gets a test using a fake/in-memory
implementation of its dependencies — see `tests/test_saved_reports.py` for
the pattern already used for the storage layer (real SQLite in a temp dir,
not mocked, because it's cheap and catches real bugs; mock only the parts
that are slow or external, like the LLM and live DB connections).
