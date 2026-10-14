"""The single composition root: the ONLY place concrete repository/factory
implementations get wired to the abstract interfaces services depend on.

Both frontends (FastAPI routers via `Depends(get_x_service)`, and Streamlit
pages via a plain function call) import from here — that's what makes them
two thin presentation layers over one shared core, not two copies of the
business logic. Nothing outside this file should construct a
SqliteConnectionRepository, SqliteReportRepository, or DefaultAgentFactory
directly.
"""

from functools import lru_cache

from dbchat.agent.factory import AgentFactory, DefaultAgentFactory
from dbchat.repositories.base import ConnectionRepository, LLMConfigRepository, ReportRepository
from dbchat.repositories.sqlite import (
    SqliteConnectionRepository,
    SqliteLLMConfigRepository,
    SqliteReportRepository,
)
from dbchat.security.rate_limiter import RateLimiter, get_rate_limiter
from dbchat.services.chat_service import ChatService
from dbchat.services.connection_service import ConnectionService
from dbchat.services.llm_config_service import LLMConfigService
from dbchat.services.report_service import ReportService


@lru_cache
def get_connection_repository() -> ConnectionRepository:
    return SqliteConnectionRepository()


@lru_cache
def get_report_repository() -> ReportRepository:
    return SqliteReportRepository()


@lru_cache
def get_llm_config_repository() -> LLMConfigRepository:
    return SqliteLLMConfigRepository()


@lru_cache
def get_agent_factory() -> AgentFactory:
    return DefaultAgentFactory()


def get_connection_service() -> ConnectionService:
    return ConnectionService(get_connection_repository())


def get_llm_config_service() -> LLMConfigService:
    return LLMConfigService(get_llm_config_repository())


def get_report_service() -> ReportService:
    return ReportService(get_report_repository(), get_agent_factory())


def get_chat_service() -> ChatService:
    rate_limiter: RateLimiter = get_rate_limiter()
    return ChatService(get_agent_factory(), rate_limiter)
