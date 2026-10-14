from fastapi import APIRouter, Depends, HTTPException

from dbchat.agent.builder import LLMNotConfiguredError
from dbchat.api.schemas.chat import ChatRequest, ChatResponse
from dbchat.deps import get_chat_service
from dbchat.services.chat_service import ChatService, RateLimitExceededError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask(payload: ChatRequest, service: ChatService = Depends(get_chat_service)):
    try:
        result = service.ask(
            connection_id=payload.connection_id,
            session_id=payload.session_id,
            history=[m.model_dump() for m in payload.history],
        )
    except RateLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't connect: {exc}") from exc
    return ChatResponse(**result)
