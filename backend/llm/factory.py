"""LLM provider factory — reads config and returns the correct adapter."""
import os

from dotenv import load_dotenv

from .base import LLMProvider
from .registry import normalize_provider_name

load_dotenv()


def get_llm_provider(provider_name: str | None = None, model: str | None = None) -> LLMProvider:
    """Create and return the configured LLM provider.

    Reads LLM_PROVIDER from environment and instantiates the correct adapter.
    Defaults to 'codex' if not set.
    """
    provider_name = normalize_provider_name(provider_name)

    if provider_name == "claude":
        from .claude_provider import ClaudeProvider

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        return ClaudeProvider(
            api_key=api_key,
            model=model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        )

    elif provider_name == "openai":
        from .openai_provider import OpenAIProvider

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return OpenAIProvider(
            api_key=api_key,
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o"),
        )

    elif provider_name == "llama":
        from .ollama_provider import OllamaProvider

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return OllamaProvider(
            base_url=base_url,
            model=model or os.getenv("OLLAMA_MODEL", "llama3"),
        )

    elif provider_name == "codex":
        from .codex_provider import CodexProvider

        return CodexProvider(model=model or os.getenv("CODEX_MODEL", "gpt-5.4"))

    elif provider_name == "copilot":
        from .copilot_provider import CopilotProvider

        return CopilotProvider(model=model or os.getenv("COPILOT_MODEL", "gpt-4.1"))

    elif provider_name == "mock":
        from .mock_provider import MockProvider

        return MockProvider()

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider_name}'. "
            f"Supported in this app: codex, copilot, llama"
        )
