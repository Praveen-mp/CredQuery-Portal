from fastapi import FastAPI

from dbchat.api.routers import chat, connections, reports, setup

app = FastAPI(
    title="dbchat API",
    description="Self-hosted, natural-language chat over your own databases.",
    version="0.1.0",
)

app.include_router(connections.router)
app.include_router(reports.router)
app.include_router(chat.router)
app.include_router(setup.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
