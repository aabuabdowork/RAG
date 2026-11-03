"""OpenRouter LLM infrastructure adapter implementing ILLMService."""
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.domain.interfaces.llm_service import ILLMService


class OpenRouterLLMService(ILLMService):
    """Adapter for interacting with OpenRouter using LangChain's ChatOpenAI."""

    def __init__(
        self,
        model: str = settings.default_model,
        base_url: str = settings.openrouter_base_url,
        api_key: str = settings.openai_api_key,
    ) -> None:
        if not api_key:
            raise ValueError("API key must be provided in environment variables (.env).")

        self._client = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
        )

    def generate(self, prompt: str) -> str:
        response = self._client.invoke(prompt)
        return str(response.content)

