import streamlit as st

from dbchat.deps import get_connection_service

connection_service = get_connection_service()

st.title("Connections", icon=":material/database:")

connections = connection_service.list()

if not connections:
    st.info("No connections yet.", icon=":material/info:")
    st.page_link("app_pages/setup.py", label="Add one on the Setup page", icon=":material/settings:")
    st.stop()


@st.dialog("Delete connection")
def confirm_delete(connection_id: int, name: str):
    st.write(f"Delete **{name}**? This cannot be undone. Any ongoing chats using it will stop working.")
    with st.container(horizontal=True):
        if st.button("Cancel", width="stretch"):
            st.rerun()
        if st.button("Delete", type="primary", icon=":material/delete:", width="stretch"):
            connection_service.delete(connection_id)
            st.rerun()


for conn in connections:
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            with st.container(gap=None):
                st.markdown(f"**{conn['name']}**")
                st.caption(f"{conn['db_type']} · {conn['host']}:{conn['port']}/{conn['database_name']}")
            if conn["readonly_confirmed"]:
                st.badge("Read-only", icon=":material/lock:", color="green")
            else:
                st.badge("Not confirmed read-only", icon=":material/warning:", color="orange")
            if st.button(
                "Delete",
                key=f"delete_{conn['id']}",
                icon=":material/delete:",
                width="content",
            ):
                confirm_delete(conn["id"], conn["name"])

st.page_link("app_pages/setup.py", label="Add another connection", icon=":material/add:")
