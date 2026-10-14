from dbchat.agent.builder import extract_query_result
from dbchat.agent.factory import AgentFactory
from dbchat.repositories.base import ReportRepository


class ReportService:
    """Use cases around saved, reusable report questions. `run` always
    queries live data through a fresh agent — a "report" here is a saved
    question, never a cached answer."""

    def __init__(self, reports: ReportRepository, agent_factory: AgentFactory):
        self._reports = reports
        self._agent_factory = agent_factory

    def save(self, *, connection_id: int, name: str, question: str) -> int:
        return self._reports.save(connection_id=connection_id, name=name, question=question)

    def list(self, connection_id: int | None = None) -> list[dict]:
        return self._reports.list(connection_id=connection_id)

    def delete(self, report_id: int) -> None:
        self._reports.delete(report_id)

    def run(self, report_id: int) -> dict:
        report = self._reports.get(report_id)
        if report is None:
            raise ValueError(f"No saved report with id={report_id}")

        agent = self._agent_factory.build(report["connection_id"])
        response = agent.invoke({"messages": [{"role": "user", "content": report["question"]}]})
        return {
            "answer": response["messages"][-1].content,
            "rows": extract_query_result(response["messages"]),
        }
