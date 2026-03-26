"""Ollama (local) LLM provider."""
import json
from typing import Any

import httpx

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Ollama local LLM adapter."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(
        self,
        prompt: str,
        system: str = "",
        response_format: str = "json",
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        system_msg = system or "You are a helpful assistant."
        if response_format == "json":
            system_msg += "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_msg,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if response_format == "json":
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("response", "")

        if response_format == "json":
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
