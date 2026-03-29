"""Shared helpers for CLI-backed LLM providers."""
import json
import re
from abc import abstractmethod
from typing import Any

from .base import LLMProvider


def _strip_code_fences(content: str) -> str:
    """Remove markdown code fences around JSON-like content."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _strip_ansi(content: str) -> str:
    """Remove terminal color codes and control sequences."""
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", content)


def _extract_json_value(content: str) -> dict[str, Any]:
    """Extract the first valid JSON object from a CLI response."""
    cleaned = _strip_code_fences(_strip_ansi(content))

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    preview = cleaned.strip().splitlines()[0][:200] if cleaned.strip() else "<empty>"
    raise RuntimeError(f"CLI model did not return valid JSON. First line: {preview}")


def _build_cli_prompt(prompt: str, system: str, response_format: str) -> str:
    """Combine system + user prompts into a single CLI-friendly instruction."""
    sections = []

    if system.strip():
        sections.append(f"SYSTEM INSTRUCTIONS:\n{system.strip()}")

    sections.append(f"USER REQUEST:\n{prompt.strip()}")

    if response_format == "json":
        sections.append(
            "RESPONSE RULES:\n"
            "Return valid JSON only.\n"
            "Do not use markdown.\n"
            "Do not wrap the JSON in code fences.\n"
            "Do not add explanation before or after the JSON."
        )
    else:
        sections.append(
            "RESPONSE RULES:\n"
            "Return plain text only.\n"
            "Do not wrap the response in markdown code fences."
        )

    return "\n\n".join(sections)


class CLIProvider(LLMProvider):
    """Base class for providers that shell out to a local CLI."""

    def __init__(self, model: str | None = None):
        self.model = model

    @abstractmethod
    async def _run_prompt(self, prompt: str) -> str:
        """Run the prompt through the backing CLI and return raw text."""
        ...

    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        del temperature
        full_prompt = _build_cli_prompt(prompt, system, response_format)
        content = await self._run_prompt(full_prompt)

        if response_format == "json":
            return _extract_json_value(content)

        return {"text": content.strip()}

    async def generate_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        result = await self.generate(prompt, system, response_format="text", temperature=temperature)
        return result["text"]
