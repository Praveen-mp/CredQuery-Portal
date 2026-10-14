from fastapi import APIRouter, Depends

from dbchat.api.schemas.llm_config import LLMConfigCreate, LLMConfigSummary
from dbchat.deps import get_llm_config_service
from dbchat.services.llm_config_service import LLMConfigService

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/llm-config", response_model=LLMConfigSummary | None)
def get_llm_config(service: LLMConfigService = Depends(get_llm_config_service)):
    config = service.get()
    if config is None:
        return None
    return LLMConfigSummary(**{k: v for k, v in config.items() if k != "api_key"})


@router.put("/llm-config", status_code=204)
def save_llm_config(payload: LLMConfigCreate, service: LLMConfigService = Depends(get_llm_config_service)):
    service.save(**payload.model_dump())
