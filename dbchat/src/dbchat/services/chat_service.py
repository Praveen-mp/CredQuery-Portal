from dbchat.agent.builder import extract_query_result, extract_tool_trace
from dbchat.agent.factory import AgentFactory
from dbchat.security.rate_limiter import RateLimiter


class RateLimitExceededError(Exception):
    """Raised instead of silently returning a rate-limit message, so the
    HTTP layer can map it to a 429 and the UI layer can map it to its own
    existing warning banner — one error type, two presentations."""

    def __init__(self, retry_after_seconds: float):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds:.0f}s")


class ChatService:
    """Use case: ask a question of one connection's agent, rate-limited per
    session. Stateless itself — the caller (UI session state, or an API
    client) owns conversation history and passes it in each call."""

    def __init__(self, agent_factory: AgentFactory, rate_limiter: RateLimiter):
        self._agent_factory = agent_factory
        self._rate_limiter = rate_limiter

    def ask(self, *, connection_id: int, session_id: str, history: list[dict]) -> dict:
        if not self._rate_limiter.allow(session_id):
            raise RateLimitExceededError(self._rate_limiter.seconds_until_next_slot(session_id))

        agent = self._agent_factory.build(connection_id)
        response = agent.invoke({"messages": history})
        return {
            "answer": response["messages"][-1].content,
            "trace": extract_tool_trace(response["messages"]),
            "rows": extract_query_result(response["messages"]),
        }
