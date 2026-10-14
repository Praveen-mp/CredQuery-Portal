import uuid

import streamlit as st

from dbchat.agent.builder import LLMNotConfiguredError
from dbchat.deps import get_chat_service, get_connection_service, get_report_service
from dbchat.reports.export import rows_to_excel_bytes, rows_to_pdf_bytes
from dbchat.services.chat_service import RateLimitExceededError
from dbchat.ui.errors import render_llm_not_configured_error

connection_service = get_connection_service()
chat_service = get_chat_service()
report_service = get_report_service()

connections = connection_service.list()

if not connections:
    st.title("Chat")
    st.info("No connections configured yet.", icon=":material/info:")
    st.page_link("app_pages/setup.py", label="Go to setup", icon=":material/settings:")
    st.stop()

options = {c["id"]: f"{c['name']} ({c['db_type']})" for c in connections}

with st.sidebar:
    st.subheader("Database", anchor=False)
    selected_id = st.selectbox(
        "Connection",
        options=list(options.keys()),
        format_func=lambda cid: options[cid],
        label_visibility="collapsed",
    )
    st.page_link("app_pages/connections.py", label="Manage connections", icon=":material/tune:")

    history_key = f"messages_{selected_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    if st.button(
        "Clear chat", icon=":material/delete_sweep:", width="stretch", disabled=not st.session_state[history_key]
    ):
        st.session_state[history_key] = []
        st.rerun()

st.title("Chat", icon=":material/chat:")
st.caption(f"Connected to **{options[selected_id]}** · read-only")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


@st.dialog("Save as report")
def save_as_report_dialog(connection_id: int, question: str):
    st.caption(f'Question: "{question}"')
    st.caption("Saved as a question you can rerun later — it always queries live data.")
    report_name = st.text_input("Report name", placeholder="e.g. Weekly signups by region")
    if st.button("Save", type="primary", icon=":material/save:", disabled=not report_name):
        report_service.save(connection_id=connection_id, name=report_name, question=question)
        st.toast(f'Saved report "{report_name}".', icon=":material/check_circle:")
        st.rerun()


for i, msg in enumerate(st.session_state[history_key]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for name, args in msg.get("trace", []):
            with st.expander(f"Called `{name}`", icon=":material/function:"):
                st.code(str(args), language="text")

        result_rows = msg.get("result_rows")
        if result_rows:
            with st.container(horizontal=True):
                st.download_button(
                    "Excel",
                    data=rows_to_excel_bytes(result_rows),
                    file_name="report.xlsx",
                    icon=":material/download:",
                    key=f"xlsx_{i}",
                )
                st.download_button(
                    "PDF",
                    data=rows_to_pdf_bytes(result_rows, title=msg.get("question", "Report")),
                    file_name="report.pdf",
                    icon=":material/download:",
                    key=f"pdf_{i}",
                )
                if st.button("Save as report", icon=":material/bookmark_add:", key=f"save_{i}"):
                    save_as_report_dialog(selected_id, msg.get("question", ""))

SUGGESTIONS = {
    ":material/list: What tables are available?": "What tables are available?",
    ":material/table_chart: How many rows are in each table?": "How many rows are in each table?",
    ":material/schema: Describe the schema": "Describe the schema of the most important tables.",
}

prompt = None
if not st.session_state[history_key]:
    selected = st.pills(
        "Try asking:", list(SUGGESTIONS.keys()), label_visibility="collapsed"
    )
    if selected:
        prompt = SUGGESTIONS[selected]

user_input = st.chat_input("Ask something about this database...")
if user_input:
    prompt = user_input

if prompt:
    st.session_state[history_key].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state[history_key]
        ]
        trace, result_rows = [], None
        try:
            with st.status(":shimmer[Querying the database]", type="compact") as status:
                result = chat_service.ask(
                    connection_id=selected_id,
                    session_id=st.session_state.session_id,
                    history=history,
                )
                trace = result["trace"]
                result_rows = result["rows"]
                for name, args in trace:
                    with st.status(f"Called `{name}`", type="step", state="complete"):
                        st.code(str(args), language="text")
                status.update(label="Done", state="complete")
            answer = result["answer"]
            st.markdown(answer)
        except RateLimitExceededError as exc:
            answer = f"Rate limit reached. Try again in {exc.retry_after_seconds:.0f}s."
            st.warning(answer, icon=":material/timer:")
        except LLMNotConfiguredError:
            answer = "No LLM provider configured yet."
            render_llm_not_configured_error()
        except Exception as exc:
            answer = (
                f"Couldn't connect using **{options[selected_id]}**. The database may be "
                f"unreachable or its credentials may have changed."
            )
            st.error(answer, icon=":material/error:")
            with st.expander("Technical details"):
                st.code(str(exc), language="text")
            st.page_link(
                "app_pages/connections.py", label="Check this connection", icon=":material/tune:"
            )

    st.session_state[history_key].append(
        {
            "role": "assistant",
            "content": answer,
            "trace": trace,
            "result_rows": result_rows,
            "question": prompt,
        }
    )
    st.rerun()
