import streamlit as st

from dbchat.agent.builder import (
    LLMNotConfiguredError,
    build_agent_for_connection,
    extract_query_result,
)
from dbchat.reports.export import rows_to_excel_bytes, rows_to_pdf_bytes
from dbchat.storage.store import delete_report, list_connections, list_reports
from dbchat.ui.errors import render_llm_not_configured_error

st.title("Reports", icon=":material/summarize:")
st.caption("Saved questions you can rerun anytime — always against live data, never a stale snapshot.")

connections = list_connections()
if not connections:
    st.info("No connections configured yet.", icon=":material/info:")
    st.page_link("app_pages/setup.py", label="Go to setup", icon=":material/settings:")
    st.stop()

options = {c["id"]: f"{c['name']} ({c['db_type']})" for c in connections}
selected_id = st.selectbox(
    "Database", options=list(options.keys()), format_func=lambda cid: options[cid]
)

reports = list_reports(connection_id=selected_id)

if not reports:
    st.info(
        "No saved reports for this connection yet. Save one from a Chat answer.",
        icon=":material/info:",
    )
    st.page_link("app_pages/chat.py", label="Go to chat", icon=":material/chat:")
    st.stop()


@st.cache_resource
def get_agent(connection_id: int):
    return build_agent_for_connection(connection_id)


for report in reports:
    result_key = f"report_result_{report['id']}"

    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            with st.container(gap=None):
                st.markdown(f"**{report['name']}**")
                st.caption(report["question"])
            if st.button("Run", icon=":material/play_arrow:", key=f"run_{report['id']}"):
                try:
                    agent = get_agent(selected_id)
                except LLMNotConfiguredError:
                    render_llm_not_configured_error()
                except Exception as exc:
                    st.error(
                        "Couldn't connect to this report's database. It may be "
                        "unreachable or its credentials may have changed.",
                        icon=":material/error:",
                    )
                    with st.expander("Technical details"):
                        st.code(str(exc), language="text")
                else:
                    with st.spinner("Running..."):
                        response = agent.invoke(
                            {"messages": [{"role": "user", "content": report["question"]}]}
                        )
                    st.session_state[result_key] = {
                        "answer": response["messages"][-1].content,
                        "rows": extract_query_result(response["messages"]),
                    }
            if st.button("Delete", icon=":material/delete:", key=f"del_{report['id']}"):
                delete_report(report["id"])
                st.session_state.pop(result_key, None)
                st.rerun()

        result = st.session_state.get(result_key)
        if result:
            st.markdown(result["answer"])
            if result["rows"]:
                with st.container(horizontal=True):
                    st.download_button(
                        "Excel",
                        data=rows_to_excel_bytes(result["rows"]),
                        file_name=f"{report['name']}.xlsx",
                        icon=":material/download:",
                        key=f"xlsx_{report['id']}",
                    )
                    st.download_button(
                        "PDF",
                        data=rows_to_pdf_bytes(result["rows"], title=report["name"]),
                        file_name=f"{report['name']}.pdf",
                        icon=":material/download:",
                        key=f"pdf_{report['id']}",
                    )
