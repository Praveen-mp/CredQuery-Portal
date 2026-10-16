import streamlit as st

from dbchat.deps import get_connection_service, get_llm_config_service

st.set_page_config(page_title="dbchat", page_icon=":material/chat:", layout="wide")

# This entry script runs before every page, regardless of which page's URL
# was requested — gating here (before nav.run()) protects the whole app, not
# just the default page. See .streamlit/secrets.toml.example for setup.
#
# st.user.get(...) rather than st.user.is_logged_in: when [auth] isn't
# configured in secrets.toml at all, the attribute form raises AttributeError
# instead of returning False — .get() degrades gracefully to "not logged in"
# so an unconfigured deployment shows the login screen instead of crashing.
if not st.user.get("is_logged_in", False):
    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        st.space("large")
        with st.container(border=True, horizontal_alignment="center"):
            st.space("small")
            st.title("dbchat", icon=":material/database:", anchor=False)
            st.caption("Enterprise database chat")
            st.write(
                "Ask questions about your company's data in plain English. "
                "Sign in with your organization account to continue."
            )
            st.space("small")
            if st.button(
                "Continue with Google", icon=":material/login:", type="primary", width="stretch"
            ):
                try:
                    st.login()
                except Exception as exc:
                    st.error(
                        "Sign-in isn't configured yet. See .streamlit/secrets.toml.example "
                        "for setup instructions.",
                        icon=":material/error:",
                    )
                    with st.expander("Technical details"):
                        st.code(str(exc), language="text")
            st.caption(":material/lock: Secured via OAuth — dbchat never sees your password.")
            st.space("small")
    st.stop()

with st.sidebar:
    st.subheader("dbchat", anchor=False)
    st.caption("Chat with your database")
    st.caption(f"Signed in as {st.user.get('name') or st.user.get('email') or 'unknown user'}")
    if st.button("Log out", icon=":material/logout:", width="stretch"):
        st.logout()

connection_service = get_connection_service()
llm_config_service = get_llm_config_service()

connections_page = st.Page(
    "app_pages/connections.py", title="Connections", icon=":material/database:"
)
reports_page = st.Page(
    "app_pages/reports.py", title="Reports", icon=":material/summarize:"
)

is_configured = llm_config_service.is_configured() and len(connection_service.list()) > 0
chat_page = st.Page("app_pages/chat.py", title="Chat", icon=":material/chat:", default=is_configured)
setup_page = st.Page("app_pages/setup.py", title="Setup", icon=":material/settings:", default=not is_configured)

nav = st.navigation([chat_page, reports_page, connections_page, setup_page])
nav.run()
