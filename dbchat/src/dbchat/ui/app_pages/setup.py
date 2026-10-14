import streamlit as st

from dbchat.adapters.registry import available_adapters
from dbchat.deps import get_connection_service, get_llm_config_service

llm_config_service = get_llm_config_service()
connection_service = get_connection_service()

st.title("Setup", icon=":material/settings:")
st.caption(
    "Configure your LLM provider and database connections. Everything below is "
    "encrypted and stored locally in this deployment's own metadata store — "
    "nothing leaves your infrastructure."
)

llm_tab, db_tab = st.tabs(["LLM provider", "Database connections"])

with llm_tab:
    existing_llm = llm_config_service.get()
    if existing_llm:
        st.caption(f"Currently configured: **{existing_llm['deployment_name']}** ({existing_llm['endpoint']})")

    with st.form("llm_config_form", border=True):
        deployment_name = st.text_input(
            "Azure deployment name", value=(existing_llm or {}).get("deployment_name", "")
        )
        endpoint = st.text_input("Azure endpoint", value=(existing_llm or {}).get("endpoint", ""))
        api_version = st.text_input(
            "API version", value=(existing_llm or {}).get("api_version", "2024-12-01-preview")
        )
        api_key = st.text_input(
            "API key",
            type="password",
            help="Leave blank to keep the currently saved key." if existing_llm else "",
        )
        submitted = st.form_submit_button("Save LLM config", icon=":material/save:", type="primary")

        if submitted:
            key_to_store = api_key or (existing_llm or {}).get("api_key", "")
            if not all([deployment_name, endpoint, api_version, key_to_store]):
                st.error("All fields are required.", icon=":material/error:")
            else:
                llm_config_service.save(
                    provider="azure_openai",
                    endpoint=endpoint,
                    deployment_name=deployment_name,
                    api_version=api_version,
                    api_key=key_to_store,
                )
                st.toast("LLM config saved.", icon=":material/check_circle:")
                st.rerun()

with db_tab:
    adapters = available_adapters()

    with st.form("new_connection_form", border=True):
        name = st.text_input("Connection name", placeholder="e.g. Production Postgres")
        db_type = st.selectbox(
            "Database type", options=list(adapters.keys()), format_func=lambda k: adapters[k]
        )
        host_col, port_col = st.columns([3, 1])
        host = host_col.text_input("Host")
        port = port_col.number_input("Port", value=5432, step=1, min_value=1, max_value=65535)
        database_name = st.text_input("Database name")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        sslmode = st.selectbox(
            "SSL mode",
            options=["prefer", "require", "disable", "verify-ca", "verify-full"],
            index=0,
            help=(
                "Most managed Postgres (RDS, Cloud SQL, Supabase, ...) needs \"require\" "
                "or stronger. \"prefer\" uses SSL if the server offers it, which works for "
                "most setups but won't catch a server that silently falls back to plaintext."
            ),
        )
        readonly_confirmed = st.checkbox(
            "I confirm this database user has read-only (SELECT-only) permissions",
            help=(
                "dbchat also rejects non-SELECT queries at the application level, "
                "but the database user itself should never have write access — "
                "that's the real safety boundary."
            ),
        )
        submitted = st.form_submit_button(
            "Test and save connection", icon=":material/database:", type="primary"
        )

        if submitted:
            if not readonly_confirmed:
                st.error(
                    "Please confirm the database user is read-only before saving.",
                    icon=":material/error:",
                )
            elif not all([name, host, database_name, username]):
                st.error("Please fill in all fields.", icon=":material/error:")
            else:
                with st.spinner("Testing connection..."):
                    ok, message = connection_service.test(
                        db_type=db_type,
                        host=host,
                        port=int(port),
                        database_name=database_name,
                        username=username,
                        password=password,
                        sslmode=sslmode,
                    )

                if not ok:
                    st.error(f"Connection failed: {message}", icon=":material/error:")
                else:
                    connection_service.create(
                        name=name,
                        db_type=db_type,
                        host=host,
                        port=int(port),
                        database_name=database_name,
                        username=username,
                        password=password,
                        sslmode=sslmode,
                        readonly_confirmed=True,
                    )
                    st.toast(f'Connection "{name}" saved.', icon=":material/check_circle:")
                    st.rerun()

    st.page_link("app_pages/connections.py", label="Manage existing connections", icon=":material/tune:")
