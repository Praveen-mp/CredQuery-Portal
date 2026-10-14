from abc import ABC, abstractmethod
from functools import lru_cache

from dbchat.agent.builder import build_agent_for_connection


class AgentFactory(ABC):
    """Services depend on this, not on build_agent_for_connection directly —
    lets a service be unit-tested with a fake factory returning a stub agent,
    with no real LLM or database connection involved."""

    @abstractmethod
    def build(self, connection_id: int): ...


class DefaultAgentFactory(AgentFactory):
    """Caches one agent (and its underlying DB connection) per connection_id
    for the lifetime of this factory instance — rebuilding an agent means
    reconnecting to the database and reconstructing the LLM client, which is
    too expensive to redo on every chat message or report run."""

    def __init__(self):
        self._build_cached = lru_cache(maxsize=None)(build_agent_for_connection)

    def build(self, connection_id: int):
        return self._build_cached(connection_id)
