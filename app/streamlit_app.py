import uuid

import streamlit as st

from agents.postgres_agent import build_postgres_agent, extract_tool_trace
from security.rate_limiter import get_rate_limiter

st.set_page_config(page_title="Postgres Q&A agent", page_icon="🗄️")
st.title("🗄️ Postgres Q&A agent")
st.caption("Ask questions about your database in plain English. Read-only — it can only SELECT.")

agent = build_postgres_agent()  # process-wide singleton (functools.lru_cache)
rate_limiter = get_rate_limiter()  # process-wide singleton, shared across sessions

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []  # each item: {"role": "user"|"assistant", "content": str}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("trace"):
            with st.expander("Show SQL / tool calls"):
                for name, args in msg["trace"]:
                    st.code(f"{name}({args})", language="text")

user_input = st.chat_input("Ask something about your database...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        if not rate_limiter.allow(st.session_state.session_id):
            wait_s = rate_limiter.seconds_until_next_slot(st.session_state.session_id)
            answer = f"Rate limit reached. Try again in {wait_s:.0f}s."
            trace = []
            st.warning(answer)
        else:
            # Pass the full conversation so far as context (simple, stateless-per-call
            # approach — no LangGraph checkpointer yet, see README Track B notes).
            history = [
                {"role": m["role"], "content": m["content"]} for m in st.session_state.messages
            ]
            with st.spinner("Querying the database..."):
                response = agent.invoke({"messages": history})
                answer = response["messages"][-1].content
                trace = extract_tool_trace(response["messages"])

            st.markdown(answer)
            if trace:
                with st.expander("Show SQL / tool calls"):
                    for name, args in trace:
                        st.code(f"{name}({args})", language="text")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "trace": trace}
    )
