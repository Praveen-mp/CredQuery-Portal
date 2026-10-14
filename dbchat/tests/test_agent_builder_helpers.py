import json

from langchain_core.messages import AIMessage, ToolMessage

from dbchat.agent.builder import extract_query_result, extract_tool_trace


def _tool_call_message(name, args, call_id="call_1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def test_extract_tool_trace_collects_all_calls():
    messages = [
        _tool_call_message("list_tables", {}),
        ToolMessage(content="users, orders", name="list_tables", tool_call_id="call_1"),
        _tool_call_message("run_select_query", {"query": "SELECT 1"}, call_id="call_2"),
        ToolMessage(content='{"row_count": 0, "rows": []}', name="run_select_query", tool_call_id="call_2"),
    ]

    trace = extract_tool_trace(messages)

    assert trace == [("list_tables", {}), ("run_select_query", {"query": "SELECT 1"})]


def test_extract_query_result_parses_last_successful_query():
    rows = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]
    messages = [
        _tool_call_message("run_select_query", {"query": "SELECT * FROM t"}),
        ToolMessage(
            content=json.dumps({"row_count": len(rows), "rows": rows}),
            name="run_select_query",
            tool_call_id="call_1",
        ),
    ]

    result = extract_query_result(messages)

    assert result == rows


def test_extract_query_result_returns_none_when_no_query_ran():
    messages = [AIMessage(content="Here's the answer without querying anything.")]

    assert extract_query_result(messages) is None


def test_extract_query_result_returns_none_on_guard_rejection():
    messages = [
        _tool_call_message("run_select_query", {"query": "DROP TABLE users"}),
        ToolMessage(
            content="Query rejected by safety guard: Only SELECT/WITH (read-only) queries are allowed.",
            name="run_select_query",
            tool_call_id="call_1",
        ),
    ]

    assert extract_query_result(messages) is None
