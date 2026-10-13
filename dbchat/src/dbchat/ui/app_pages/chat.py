import uuid

import streamlit as st

from dbchat.agent.builder import build_agent_for_connection, extract_tool_trace
from dbchat.security.rate_limiter import get_rate_limiter
from dbchat.storage.store import list_connections

st.title("Chat")

connections = list_connections()
if not connections:
    st.info("No connections configured yet. Go to Setup to add one.", icon=":material/info:")
    st.stop()

options = {c["id"]: f"{c['name']} ({c['db_type']})" for c in connections}
selected_id = st.selectbox(
    "Database",
    options=list(options.keys()),
    format_func=lambda cid: options[cid],
)


@st.cache_resource
def get_agent(connection_id: int):
    return build_agent_for_connection(connection_id)


agent = get_agent(selected_id)
rate_limiter = get_rate_limiter()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

history_key = f"messages_{selected_id}"
if history_key not in st.session_state:
    st.session_state[history_key] = []

for msg in st.session_state[history_key]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for name, args in msg.get("trace", []):
            with st.expander(f"Called `{name}`", icon=":material/function:"):
                st.code(str(args), language="text")

user_input = st.chat_input("Ask something about this database...")

if user_input:
    st.session_state[history_key].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

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
