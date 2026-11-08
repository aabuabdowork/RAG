import time
from typing import Optional

from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.domain.exceptions import ServiceUnavailableError
from src.domain.interfaces.llm_service import ILLMService
from src.domain.interfaces.metrics import IMetrics

USAGE = {"usage": {"include": True}}


class OpenRouterLLMService(ILLMService):
    def __init__(
        self,
        model: str = settings.default_model,
        fallback_model: str = settings.fallback_model,
        base_url: str = settings.openrouter_base_url,
        api_key: str = settings.openai_api_key,
        max_tokens: int = settings.max_output_tokens,
        temperature: float = settings.llm_temperature,
        timeout: float = settings.llm_timeout,
        max_retries: int = settings.llm_max_retries,
        metrics: Optional[IMetrics] = None,
    ) -> None:
        if not api_key:
            raise ValueError("API key must be provided in environment variables (.env).")

        def chat(name: str) -> ChatOpenAI:
            return ChatOpenAI(
                model=name,
                base_url=base_url,
                api_key=api_key,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                max_retries=max_retries,
                extra_body=USAGE,
            )

        primary = chat(model)
        use_fallback = fallback_model and fallback_model != model
        self._client = primary.with_fallbacks([chat(fallback_model)]) if use_fallback else primary
        self._metrics = metrics

    def generate(self, prompt: str, system: str = "", name: str = "llm") -> str:
        messages = [("system", system), ("human", prompt)] if system else [("human", prompt)]
        started = time.perf_counter()
        try:
            response = self._client.invoke(messages, config={"run_name": name})
        except Exception as error:
            self._record(name, started, status="error", error=type(error).__name__)
            raise ServiceUnavailableError("LLM", error) from error

        usage = response.response_metadata.get("token_usage") or {}
        self._record(
            name,
            started,
            status="ok",
            model=response.response_metadata.get("model_name"),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            cost=usage.get("cost", 0.0),
        )
        return str(response.content)

    def _record(self, name: str, started: float, **fields) -> None:
        if self._metrics:
            latency_ms = round((time.perf_counter() - started) * 1000)
            self._metrics.record("llm", name=name, latency_ms=latency_ms, **fields)
