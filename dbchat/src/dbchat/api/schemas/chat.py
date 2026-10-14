from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    connection_id: int
    session_id: str
    history: list[ChatMessage]


class ChatResponse(BaseModel):
    answer: str
    trace: list[tuple[str, dict]]
    rows: list[dict] | None = None
