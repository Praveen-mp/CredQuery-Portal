from fastapi import Depends, FastAPI

from dbchat.api.auth import require_api_key
from dbchat.api.routers import chat, connections, reports, setup

app = FastAPI(
    title="dbchat API",
    description="Self-hosted, natural-language chat over your own databases.",
    version="0.1.0",
)

# /health deliberately excluded — load balancers/orchestrators need to hit it
# without a token. Every other route requires the API key (see api/auth.py).
_auth = [Depends(require_api_key)]
app.include_router(connections.router, dependencies=_auth)
app.include_router(reports.router, dependencies=_auth)
app.include_router(chat.router, dependencies=_auth)
app.include_router(setup.router, dependencies=_auth)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
