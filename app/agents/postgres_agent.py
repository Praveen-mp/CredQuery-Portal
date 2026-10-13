from functools import lru_cache

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from core.config import get_settings
from db.postgres import get_postgres_db
from security.sql_guard import UnsafeQueryError, ensure_safe_select


def _build_tools():
    db = get_postgres_db()

    @tool
    def list_tables() -> str:
        """List every table name available in the database."""
        return ", ".join(db.get_usable_table_names())

    @tool
    def get_schema(table_names: str) -> str:
        """Get column names and types for a comma-separated list of table names.
        Call this before writing a query against tables you haven't inspected yet."""
        names = [t.strip() for t in table_names.split(",") if t.strip()]
        return db.get_table_info(table_names=names)

    @tool
    def run_select_query(query: str) -> str:
        """Run a single read-only SQL SELECT (or WITH ... SELECT) query and
        return the result. Only SELECT queries are permitted — INSERT, UPDATE,
        DELETE, DROP, ALTER, and any other mutating or multi-statement query
        will be rejected before it ever reaches the database."""
        try:
            safe_query = ensure_safe_select(query)
        except UnsafeQueryError as exc:
            return f"Query rejected by safety guard: {exc}"
        try:
            return db.run(safe_query)
        except Exception as exc:  # surface DB errors back to the model, don't crash
            return f"Database error: {exc}"

    return [list_tables, get_schema, run_select_query]


@lru_cache
def build_postgres_agent():
    """Builds a read-only, tool-calling SQL agent over the configured Postgres DB.
    Cached as a process-wide singleton — call this once, reuse the returned agent."""
    settings = get_settings()

    llm = init_chat_model(
        f"azure_openai:{settings.azure_openai_deployment_name}",
        azure_deployment=settings.azure_openai_deployment_name,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

    db = get_postgres_db()
    tools = _build_tools()

    system_prompt = f"""You are a read-only Postgres database assistant.
You must NEVER attempt to modify data or schema. Only SELECT queries are
possible — your run_select_query tool will reject anything else.

When answering:
1. Call list_tables if you don't already know what tables exist.
2. Call get_schema for only the tables relevant to the question.
3. Write a single SELECT query for the {db.dialect} dialect.
4. Run it with run_select_query.
5. Answer the user's question in plain language based on the result.
"""

    return create_agent(model=llm, tools=tools, system_prompt=system_prompt)


def extract_tool_trace(messages):
    """Pulls out (tool_name, args) pairs from an agent response's message list,
    so the UI can show what actually ran."""
    trace = []
    for msg in messages:
        for tc in getattr(msg, "tool_calls", None) or []:
            trace.append((tc["name"], tc["args"]))
    return trace
