import uuid

import streamlit as st

from dbchat.agent.builder import (
    LLMNotConfiguredError,
    build_agent_for_connection,
    extract_tool_trace,
)
from dbchat.security.rate_limiter import get_rate_limiter
from dbchat.storage.store import list_connections

connections = list_connections()

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


@st.cache_resource
def get_agent(connection_id: int):
    return build_agent_for_connection(connection_id)


try:
    agent = get_agent(selected_id)
except LLMNotConfiguredError:
    st.error("No LLM provider configured yet.", icon=":material/error:")
    st.page_link(
        "app_pages/setup.py", label="Complete LLM setup", icon=":material/settings:"
    )
    st.stop()
except Exception as exc:
    st.error(
        f"Couldn't connect using **{options[selected_id]}**. The database may be "
        f"unreachable or its credentials may have changed.",
        icon=":material/error:",
    )
    with st.expander("Technical details"):
        st.code(str(exc), language="text")
    st.page_link(
        "app_pages/connections.py", label="Check this connection", icon=":material/tune:"
    )
    st.stop()

rate_limiter = get_rate_limiter()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

for msg in st.session_state[history_key]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for name, args in msg.get("trace", []):
            with st.expander(f"Called `{name}`", icon=":material/function:"):
                st.code(str(args), language="text")

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
        if not rate_limiter.allow(st.session_state.session_id):
            wait_s = rate_limiter.seconds_until_next_slot(st.session_state.session_id)
            answer = f"Rate limit reached. Try again in {wait_s:.0f}s."
            trace = []
            st.warning(answer, icon=":material/timer:")
        else:
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state[history_key]
            ]
            with st.status(":shimmer[Querying the database]", type="compact") as status:
                response = agent.invoke({"messages": history})
                trace = extract_tool_trace(response["messages"])
                for name, args in trace:
                    with st.status(f"Called `{name}`", type="step", state="complete"):
                        st.code(str(args), language="text")
                status.update(label="Done", state="complete")

            answer = response["messages"][-1].content
            st.markdown(answer)

    st.session_state[history_key].append(
        {"role": "assistant", "content": answer, "trace": trace}
    )
    st.rerun()
