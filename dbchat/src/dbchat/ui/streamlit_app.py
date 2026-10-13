import streamlit as st

from dbchat.storage.store import get_llm_config, list_connections

st.set_page_config(page_title="dbchat", page_icon=":material/chat:", layout="wide")

with st.sidebar:
    st.subheader("dbchat", anchor=False)
    st.caption("Chat with your database")

connections_page = st.Page(
    "app_pages/connections.py", title="Connections", icon=":material/database:"
)

is_configured = get_llm_config() is not None and len(list_connections()) > 0
chat_page = st.Page("app_pages/chat.py", title="Chat", icon=":material/chat:", default=is_configured)
setup_page = st.Page("app_pages/setup.py", title="Setup", icon=":material/settings:", default=not is_configured)

nav = st.navigation([chat_page, connections_page, setup_page])
nav.run()
