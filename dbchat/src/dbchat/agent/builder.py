import json

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from dbchat.adapters.registry import get_adapter_class
from dbchat.security.sql_guard import UnsafeQueryError, ensure_safe_select
from dbchat.storage.store import get_connection_with_password, get_llm_config


class LLMNotConfiguredError(RuntimeError):
    """Raised when no LLM provider has been saved yet. Distinct from a DB
    connection failure so the UI can point the user at the right fix."""


def _build_llm():
    llm_config = get_llm_config()
    if llm_config is None:
        raise LLMNotConfiguredError("No LLM provider configured yet — complete Setup first.")

    if llm_config["provider"] != "azure_openai":
        raise NotImplementedError(f"Provider {llm_config['provider']!r} not supported yet.")

    return init_chat_model(
        f"azure_openai:{llm_config['deployment_name']}",
        azure_deployment=llm_config["deployment_name"],
        azure_endpoint=llm_config["endpoint"],
        api_key=llm_config["api_key"],
        api_version=llm_config["api_version"],
    )


def _build_tools(adapter):
    @tool
    def list_tables() -> str:
        """List every table name available in the database."""
        return ", ".join(adapter.list_tables())

    @tool
    def get_schema(table_names: str) -> str:
        """Get column names and types for a comma-separated list of table names.
        Call this before writing a query against tables you haven't inspected yet."""
        names = [t.strip() for t in table_names.split(",") if t.strip()]
        return adapter.get_schema(names)

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
            rows = adapter.run_query(safe_query)
        except Exception as exc:  # surface DB errors back to the model, don't crash
            return f"Database error: {exc}"
        # JSON so the model can read it AND the UI can parse the same string
        # back out for Excel/PDF export and "save as report" — single channel,
        # no separate side-state to keep in sync.
        return json.dumps({"row_count": len(rows), "rows": rows})

    return [list_tables, get_schema, run_select_query]


def build_agent_for_connection(connection_id: int):
    """Builds a fresh agent wired to one saved, user-configured connection.
    Not cached at this layer — callers (the UI) decide caching granularity,
    typically one cached agent per connection_id."""
    connection = get_connection_with_password(connection_id)
    if connection is None:
        raise ValueError(f"No saved connection with id={connection_id}")

    adapter_cls = get_adapter_class(connection["db_type"])
    adapter = adapter_cls(connection)

    llm = _build_llm()
    tools = _build_tools(adapter)

    system_prompt = f"""You are a read-only database assistant for the connection "{connection['name']}".
You must NEVER attempt to modify data or schema. Only SELECT queries are
possible — your run_select_query tool will reject anything else.

When answering:
1. Call list_tables if you don't already know what tables exist.
2. Call get_schema for only the tables relevant to the question.
3. Write a single SELECT query for the {adapter.dialect} dialect.
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


def extract_query_result(messages) -> list[dict] | None:
    """Pulls the rows from the most recent successful run_select_query call
    in this response, for the UI's export/save-as-report features. Returns
    None if no query ran, or it ran but returned no rows/failed."""
    for msg in reversed(messages):
        if getattr(msg, "name", None) != "run_select_query":
            continue
        try:
            parsed = json.loads(msg.content)
        except (json.JSONDecodeError, TypeError):
            continue
        rows = parsed.get("rows")
        if rows:
            return rows
    return None
