"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract LLM provider interface.

    All LLM adapters (Claude, OpenAI, Ollama, Mock) implement this interface
    so the rest of the application can swap providers via config.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt.
            system: System prompt for context setting.
            response_format: Expected response format ('json' or 'text').
            temperature: Creativity parameter (0.0 - 1.0).

        Returns:
            Parsed JSON dict if response_format is 'json', else {'text': response}.
        """
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        """Generate a plain text response from the LLM.

        Args:
            prompt: The user prompt.
            system: System prompt for context setting.
            temperature: Creativity parameter.

        Returns:
            Plain text response string.
        """
        ...
