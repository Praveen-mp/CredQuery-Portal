import streamlit as st


def render_llm_not_configured_error() -> None:
    """Shared by every page that builds an agent (Chat, Reports) — they all
    need to fail the same way when no LLM provider has been saved yet."""
    st.error("No LLM provider configured yet.", icon=":material/error:")
    st.page_link("app_pages/setup.py", label="Complete LLM setup", icon=":material/settings:")
