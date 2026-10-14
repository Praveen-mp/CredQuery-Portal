from dbchat.repositories.base import ConnectionRepository, LLMConfigRepository, ReportRepository
from dbchat.storage import store


class SqliteConnectionRepository(ConnectionRepository):
    """Thin adapter from the ConnectionRepository interface onto the existing
    storage.store module-level functions — no new persistence logic here."""

    def save(self, **kwargs) -> int:
        return store.save_connection(**kwargs)

    def list(self) -> list[dict]:
        return store.list_connections()

    def get_with_credentials(self, connection_id: int) -> dict | None:
        return store.get_connection_with_password(connection_id)

    def delete(self, connection_id: int) -> None:
        store.delete_connection(connection_id)


class SqliteReportRepository(ReportRepository):
    def save(self, *, connection_id: int, name: str, question: str) -> int:
        return store.save_report(connection_id=connection_id, name=name, question=question)

    def list(self, connection_id: int | None = None) -> list[dict]:
        return store.list_reports(connection_id=connection_id)

    def get(self, report_id: int) -> dict | None:
        return store.get_report(report_id)

    def delete(self, report_id: int) -> None:
        store.delete_report(report_id)


class SqliteLLMConfigRepository(LLMConfigRepository):
    def save(self, **kwargs) -> None:
        store.save_llm_config(**kwargs)

    def get(self) -> dict | None:
        return store.get_llm_config()
