import streamlit as st

from dbchat.storage.store import delete_connection, list_connections

st.title("Connections")

connections = list_connections()

if not connections:
    st.info("No connections yet. Add one on the Setup page.", icon=":material/info:")
else:
    for conn in connections:
        with st.container(border=True, horizontal=True, vertical_alignment="center"):
            st.markdown(
                f"**{conn['name']}** · {conn['db_type']} · "
                f"`{conn['host']}:{conn['port']}/{conn['database_name']}`"
            )
            if st.button(
                "Delete", key=f"delete_{conn['id']}", icon=":material/delete:", width="content"
            ):
                delete_connection(conn["id"])
                st.rerun()
