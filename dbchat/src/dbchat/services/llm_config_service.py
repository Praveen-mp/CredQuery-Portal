from dbchat.repositories.base import LLMConfigRepository


class LLMConfigService:
    """Use cases around the deployment's single LLM provider configuration."""

    def __init__(self, llm_config: LLMConfigRepository):
        self._llm_config = llm_config

    def save(
        self, *, provider: str = "azure_openai", endpoint: str, deployment_name: str,
        api_version: str, api_key: str,
    ) -> None:
        self._llm_config.save(
            provider=provider,
            endpoint=endpoint,
            deployment_name=deployment_name,
            api_version=api_version,
            api_key=api_key,
        )

    def get(self) -> dict | None:
        """Includes the decrypted API key — callers serving this to a UI/API
        response must strip it first. See LLMConfigSummary in api/schemas."""
        return self._llm_config.get()

    def is_configured(self) -> bool:
        return self.get() is not None
