from fastapi import Header, HTTPException

from dbchat.core.config import get_app_settings


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    """Simple shared-secret auth for the API: `Authorization: Bearer <token>`.

    This is deliberately NOT the same mechanism as the Streamlit UI's real,
    per-user OIDC login (st.login) — a browser OAuth redirect flow doesn't
    apply to a JSON API consumed programmatically. A single pre-shared token
    is adequate for internal tooling / service-to-service access, but it has
    no concept of per-user identity or an audit trail — don't present this as
    equivalent to the UI's auth.

    If AppSettings.api_key isn't configured, this is a no-op and the API is
    open. That's a deliberate default for local dev, not a recommendation —
    set API_KEY before exposing this past localhost.
    """
    settings = get_app_settings()
    if settings.api_key is None:
        return

    expected = f"Bearer {settings.api_key}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
