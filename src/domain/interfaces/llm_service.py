"""Interface contract for LLM services."""
from abc import ABC, abstractmethod


class ILLMService(ABC):
    """Abstract interface for LLM interactions."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response given a text prompt."""
        pass

