"""OpenAI LLM provider."""
import json
from typing import Any

from openai import AsyncOpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API adapter."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        messages = []
        sys_content = system or "You are a helpful assistant."
        if response_format == "json":
            sys_content += "\n\nYou MUST respond with valid JSON only."
        messages.append({"role": "system", "content": sys_content})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        if response_format == "json":
            return json.loads(content)

        return {"text": content}

    async def generate_text(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
    ) -> str:
        result = await self.generate(prompt, system, response_format="text", temperature=temperature)
        return result["text"]
