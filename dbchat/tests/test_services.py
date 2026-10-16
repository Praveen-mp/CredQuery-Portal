import pytest

from dbchat.adapters.base import BaseDBAdapter
from dbchat.adapters.registry import register
from dbchat.agent.factory import AgentFactory
from dbchat.repositories.base import ConnectionRepository, ReportRepository
from dbchat.security.rate_limiter import RateLimiter
from dbchat.services.chat_service import ChatService, RateLimitExceededError
from dbchat.services.connection_service import ConnectionService
from dbchat.services.report_service import ReportService


@register
class FakeDBAdapter(BaseDBAdapter):
    """Registered under a throwaway key so ConnectionService.test()'s
    orchestration logic (connect -> verify_read_only -> combined result) can
    be exercised through the real adapters.registry lookup, with a
    controllable result, instead of a live database."""

    key = "fake_test_db"
    display_name = "Fake (test only)"

    # Class-level, set per-test, since ConnectionService.test() constructs
    # a fresh instance via the registry rather than taking one as an argument.
    connection_ok: bool = True
    read_only: bool | None = True
    read_only_message: str = "No write privileges detected for this user."

    def __init__(self, connection: dict):
        pass

    def test_connection(self) -> tuple[bool, str]:
        return self.connection_ok, "ok" if self.connection_ok else "connection failed"

    def verify_read_only(self) -> tuple[bool | None, str]:
        return self.read_only, self.read_only_message

    def list_tables(self) -> list[str]:
        return []

    def get_schema(self, table_names: list[str]) -> str:
        return ""

    def run_query(self, query: str) -> list[dict]:
        return []

    @property
    def dialect(self) -> str:
        return "fake"

    @property
    def row_limit(self) -> int:
        return 500


class FakeConnectionRepository(ConnectionRepository):
    """In-memory fake — proves ConnectionService can be tested with zero
    database involvement, which is the entire point of depending on the
    ConnectionRepository interface instead of storage.store directly."""

    def __init__(self):
        self._rows: dict[int, dict] = {}
        self._next_id = 1

    def save(self, **kwargs) -> int:
        connection_id = self._next_id
        self._next_id += 1
        self._rows[connection_id] = {"id": connection_id, **kwargs}
        return connection_id

    def list(self) -> list[dict]:
        return [{k: v for k, v in row.items() if k != "password"} for row in self._rows.values()]

    def get_with_credentials(self, connection_id: int) -> dict | None:
        return self._rows.get(connection_id)

    def delete(self, connection_id: int) -> None:
        self._rows.pop(connection_id, None)


class FakeReportRepository(ReportRepository):
    def __init__(self):
        self._rows: dict[int, dict] = {}
        self._next_id = 1

    def save(self, *, connection_id, name, question) -> int:
        report_id = self._next_id
        self._next_id += 1
        self._rows[report_id] = {
            "id": report_id, "connection_id": connection_id, "name": name, "question": question,
        }
        return report_id

    def list(self, connection_id=None) -> list[dict]:
        rows = self._rows.values()
        if connection_id is not None:
            rows = [r for r in rows if r["connection_id"] == connection_id]
        return list(rows)

    def get(self, report_id: int) -> dict | None:
        return self._rows.get(report_id)

    def delete(self, report_id: int) -> None:
        self._rows.pop(report_id, None)


class FakeAgent:
    def __init__(self, answer: str):
        self._answer = answer

    def invoke(self, _payload):
        return {"messages": [type("Msg", (), {"content": self._answer, "tool_calls": []})()]}


class FakeAgentFactory(AgentFactory):
    def __init__(self, answer: str = "42"):
        self._answer = answer
        self.built_for: list[int] = []

    def build(self, connection_id: int):
        self.built_for.append(connection_id)
        return FakeAgent(self._answer)


def test_connection_service_rejects_unconfirmed_readonly():
    service = ConnectionService(FakeConnectionRepository())

    with pytest.raises(ValueError, match="read-only"):
        service.create(
            name="x", db_type="postgres", host="h", port=5432, database_name="d",
            username="u", password="p", readonly_confirmed=False,
        )


def test_connection_service_create_list_delete():
    repo = FakeConnectionRepository()
    service = ConnectionService(repo)

    connection_id = service.create(
        name="Prod", db_type="postgres", host="h", port=5432, database_name="d",
        username="u", password="secret", readonly_confirmed=True,
    )

    listed = service.list()
    assert len(listed) == 1
    assert listed[0]["id"] == connection_id
    assert "password" not in listed[0]

    service.delete(connection_id)
    assert service.list() == []


def _test_connection_kwargs(**overrides):
    kwargs = {
        "db_type": "fake_test_db", "host": "h", "port": 5432, "database_name": "d",
        "username": "u", "password": "p",
    }
    kwargs.update(overrides)
    return kwargs


def test_connection_service_test_blocks_when_write_access_detected():
    FakeDBAdapter.connection_ok = True
    FakeDBAdapter.read_only = False
    FakeDBAdapter.read_only_message = "This user has INSERT privilege on at least one table."
    service = ConnectionService(FakeConnectionRepository())

    ok, message = service.test(**_test_connection_kwargs())

    assert ok is False
    assert "NOT read-only" in message
    assert "INSERT" in message


def test_connection_service_test_passes_when_confirmed_read_only():
    FakeDBAdapter.connection_ok = True
    FakeDBAdapter.read_only = True
    FakeDBAdapter.read_only_message = "No write privileges detected for this user."
    service = ConnectionService(FakeConnectionRepository())

    ok, message = service.test(**_test_connection_kwargs())

    assert ok is True
    assert "Connected successfully" in message


def test_connection_service_test_allows_but_flags_when_unverifiable():
    FakeDBAdapter.connection_ok = True
    FakeDBAdapter.read_only = None
    FakeDBAdapter.read_only_message = "permission denied for information_schema"
    service = ConnectionService(FakeConnectionRepository())

    ok, message = service.test(**_test_connection_kwargs())

    # Can't be confirmed, so it isn't silently treated as safe — but it also
    # isn't a hard block, since we can't prove it's actually unsafe either.
    assert ok is True
    assert "double-check this manually" in message


def test_connection_service_test_fails_fast_when_connection_itself_fails():
    FakeDBAdapter.connection_ok = False
    service = ConnectionService(FakeConnectionRepository())

    ok, message = service.test(**_test_connection_kwargs())

    assert ok is False
    assert message == "connection failed"


def test_report_service_run_uses_live_agent_not_a_cached_answer():
    reports = FakeReportRepository()
    agent_factory = FakeAgentFactory(answer="There are 42 rows.")
    service = ReportService(reports, agent_factory)

    report_id = service.save(connection_id=7, name="Row count", question="How many rows?")

    result = service.run(report_id)

    assert result["answer"] == "There are 42 rows."
    assert agent_factory.built_for == [7]  # built fresh for this connection, not reused from elsewhere


def test_report_service_run_raises_for_unknown_report():
    service = ReportService(FakeReportRepository(), FakeAgentFactory())

    with pytest.raises(ValueError, match="No saved report"):
        service.run(999)


def test_chat_service_raises_when_rate_limited():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    service = ChatService(FakeAgentFactory(), limiter)

    service.ask(connection_id=1, session_id="s1", history=[{"role": "user", "content": "hi"}])

    with pytest.raises(RateLimitExceededError):
        service.ask(connection_id=1, session_id="s1", history=[{"role": "user", "content": "hi again"}])


def test_chat_service_different_sessions_have_independent_limits():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    service = ChatService(FakeAgentFactory(), limiter)

    service.ask(connection_id=1, session_id="s1", history=[])
    # A different session is not blocked by session s1's limit.
    service.ask(connection_id=1, session_id="s2", history=[])
