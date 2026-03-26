"""Claude (Anthropic) LLM provider."""
import json
from typing import Any

from anthropic import AsyncAnthropic

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API adapter."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        system_msg = system
        if response_format == "json":
            system_msg += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation, just JSON."

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=temperature,
            system=system_msg if system_msg else "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )

        content = message.content[0].text

        if response_format == "json":
            # Strip markdown code fences if present
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text.strip())

        return {"text": content}

    async def generate_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        result = await self.generate(prompt, system, response_format="text", temperature=temperature)
        return result["text"]
