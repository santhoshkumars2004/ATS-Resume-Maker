"""Provider normalization and availability reporting."""
import os
import shutil
from typing import Any

DEFAULT_PROVIDER = "codex"

CODEX_MODEL_OPTIONS = [
    {"value": "gpt-5.4", "label": "GPT-5.4"},
    {"value": "gpt-5.4-mini", "label": "GPT-5.4-Mini"},
    {"value": "gpt-5.3-codex", "label": "GPT-5.3-Codex"},
    {"value": "gpt-5.3-codex-spark-preview", "label": "GPT-5.3-Codex-Spark-Preview"},
    {"value": "gpt-5.2-codex", "label": "GPT-5.2-Codex"},
    {"value": "gpt-5.2", "label": "GPT-5.2"},
    {"value": "gpt-5.1-codex-max", "label": "GPT-5.1-Codex-Max"},
    {"value": "gpt-5.1-codex-mini", "label": "GPT-5.1-Codex-Mini"},
]

COPILOT_MODEL_OPTIONS = [
    {"value": "gpt-4.1", "label": "GPT-4.1"},
    {"value": "gpt-4o", "label": "GPT-4o"},
    {"value": "gpt-5-mini", "label": "GPT-5 mini"},
    {"value": "claude-haiku-4.5", "label": "Claude Haiku 4.5"},
    {"value": "claude-opus-4.5", "label": "Claude Opus 4.5"},
    {"value": "claude-opus-4.6", "label": "Claude Opus 4.6"},
    {"value": "claude-sonnet-4", "label": "Claude Sonnet 4"},
    {"value": "claude-sonnet-4.5", "label": "Claude Sonnet 4.5"},
    {"value": "claude-sonnet-4.6", "label": "Claude Sonnet 4.6"},
    {"value": "gemini-3-flash-preview", "label": "Gemini 3 Flash (Preview)"},
    {"value": "gpt-5.1-codex", "label": "GPT-5.1-Codex"},
    {"value": "gpt-5.1-codex-mini", "label": "GPT-5.1-Codex-Mini (Preview)"},
    {"value": "gpt-5.2", "label": "GPT-5.2"},
    {"value": "gpt-5.2-codex", "label": "GPT-5.2-Codex"},
    {"value": "gpt-5.3-codex", "label": "GPT-5.3-Codex"},
    {"value": "gpt-5.4", "label": "GPT-5.4"},
]

LLAMA_MODEL_OPTIONS = [
    {"value": "llama3", "label": "llama3"},
    {"value": "llama3.1", "label": "llama3.1"},
    {"value": "llama3.2", "label": "llama3.2"},
    {"value": "llama3.3", "label": "llama3.3"},
    {"value": "qwen2.5-coder", "label": "qwen2.5-coder"},
    {"value": "mistral", "label": "mistral"},
    {"value": "deepseek-r1", "label": "deepseek-r1"},
]

PROVIDER_ALIASES = {
    "codex": "codex",
    "codex_cli": "codex",
    "copilot": "copilot",
    "copilot_cli": "copilot",
    "llama": "llama",
    "ollama": "llama",
}


def normalize_provider_name(provider_name: str | None) -> str:
    """Normalize aliases and fall back to the configured default provider."""
    if provider_name is None:
        raw_name = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).lower().strip()
        return PROVIDER_ALIASES.get(raw_name, DEFAULT_PROVIDER)

    raw_name = provider_name.lower().strip()
    return PROVIDER_ALIASES.get(raw_name, raw_name)


def get_provider_options() -> list[dict[str, Any]]:
    """Return provider metadata for the frontend."""
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "").strip()

    options = [
        {
            "id": "codex",
            "label": "Codex CLI",
            "available": bool(shutil.which("codex")),
            "supports_model_override": True,
            "default_model": os.getenv("CODEX_MODEL", "gpt-5.4"),
            "supported_models": CODEX_MODEL_OPTIONS,
            "reason": None if shutil.which("codex") else "codex CLI not found in PATH.",
        },
        {
            "id": "copilot",
            "label": "GitHub Copilot CLI",
            "available": bool(shutil.which("copilot") or shutil.which("gh")),
            "supports_model_override": True,
            "default_model": os.getenv("COPILOT_MODEL", "gpt-4.1"),
            "supported_models": COPILOT_MODEL_OPTIONS,
            "reason": None if (shutil.which("copilot") or shutil.which("gh")) else "GitHub Copilot CLI not found in PATH.",
        },
        {
            "id": "llama",
            "label": "Llama via Ollama",
            "available": bool(shutil.which("ollama") or ollama_base_url),
            "supports_model_override": True,
            "default_model": os.getenv("OLLAMA_MODEL", "llama3"),
            "supported_models": LLAMA_MODEL_OPTIONS,
            "supports_custom_model": True,
            "reason": None if (shutil.which("ollama") or ollama_base_url) else "Ollama is not installed and OLLAMA_BASE_URL is not set.",
        },
    ]

    return options
