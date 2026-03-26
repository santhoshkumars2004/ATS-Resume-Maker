"""LLM provider factory — reads config and returns the correct adapter."""
import os

from dotenv import load_dotenv

from .base import LLMProvider

load_dotenv()


def get_llm_provider() -> LLMProvider:
    """Create and return the configured LLM provider.

    Reads LLM_PROVIDER from environment and instantiates the correct adapter.
    Defaults to 'mock' if not set.
    """
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower().strip()

    if provider_name == "claude":
        from .claude_provider import ClaudeProvider

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        return ClaudeProvider(api_key=api_key)

    elif provider_name == "openai":
        from .openai_provider import OpenAIProvider

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return OpenAIProvider(api_key=api_key)

    elif provider_name == "ollama":
        from .ollama_provider import OllamaProvider

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3")
        return OllamaProvider(base_url=base_url, model=model)

    elif provider_name == "mock":
        from .mock_provider import MockProvider

        return MockProvider()

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider_name}'. "
            f"Supported: claude, openai, ollama, mock"
        )
