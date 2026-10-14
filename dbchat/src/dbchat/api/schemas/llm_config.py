from pydantic import BaseModel


class LLMConfigCreate(BaseModel):
    provider: str = "azure_openai"
    endpoint: str
    deployment_name: str
    api_version: str
    api_key: str


class LLMConfigSummary(BaseModel):
    """Intentionally excludes api_key — never return a stored secret in a response."""

    provider: str
    endpoint: str
    deployment_name: str
    api_version: str
