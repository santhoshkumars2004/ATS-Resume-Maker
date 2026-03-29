"""Codex CLI-backed LLM provider."""
import asyncio
import tempfile
from time import perf_counter
from pathlib import Path

from backend.logging_utils import log_event
from .cli_base import CLIProvider

DEFAULT_CODEX_MODEL = "gpt-5-codex"
CHATGPT_UNSUPPORTED_MODEL_ERROR = "not supported when using codex with a chatgpt account"
DEFAULT_CODEX_REASONING_EFFORT = "high"
UNSUPPORTED_REASONING_ERROR = "unsupported value: 'xhigh'"


class CodexProvider(CLIProvider):
    """Use the local Codex CLI as the model backend."""

    def __init__(self, model: str = DEFAULT_CODEX_MODEL, workdir: str | Path | None = None):
        super().__init__(model=model)
        self.workdir = Path(workdir or Path.cwd())

    async def _execute_prompt(self, prompt: str, model: str, reasoning_effort: str = DEFAULT_CODEX_REASONING_EFFORT) -> str:
        stage_started = perf_counter()
        log_event("llm", "CODEX", f"dispatching request | model={model} reasoning={reasoning_effort}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as handle:
            output_path = Path(handle.name)

        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-c",
            f'model_reasoning_effort="{reasoning_effort}"',
            "--output-last-message",
            str(output_path),
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.append("-")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.workdir),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate(prompt.encode("utf-8"))
        stdout_text = stdout.decode("utf-8", errors="ignore").strip()
        stderr_text = stderr.decode("utf-8", errors="ignore").strip()

        try:
            if process.returncode != 0:
                raise RuntimeError(stderr_text or stdout_text or "Codex CLI exited with a non-zero status.")

            content = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            if content:
                log_event("llm", "CODEX", f"response received in {perf_counter() - stage_started:.2f}s")
                return content

            if stdout_text:
                log_event("llm", "CODEX", f"response received in {perf_counter() - stage_started:.2f}s")
                return stdout_text

            raise RuntimeError("Codex CLI returned an empty response.")
        finally:
            output_path.unlink(missing_ok=True)

    async def _run_prompt(self, prompt: str) -> str:
        requested_model = self.model or DEFAULT_CODEX_MODEL

        try:
            return await self._execute_prompt(prompt, requested_model)
        except RuntimeError as exc:
            message = str(exc)
            if requested_model != DEFAULT_CODEX_MODEL and CHATGPT_UNSUPPORTED_MODEL_ERROR in message.lower():
                log_event(
                    "llm",
                    "CODEX",
                    f"requested model unsupported for current login | requested={requested_model} fallback={DEFAULT_CODEX_MODEL}",
                )
                self.model = DEFAULT_CODEX_MODEL
                return await self._execute_prompt(prompt, DEFAULT_CODEX_MODEL)

            if UNSUPPORTED_REASONING_ERROR in message.lower():
                log_event(
                    "llm",
                    "CODEX",
                    f"retrying with supported reasoning effort | model={requested_model} fallback_reasoning={DEFAULT_CODEX_REASONING_EFFORT}",
                )
                return await self._execute_prompt(prompt, requested_model, DEFAULT_CODEX_REASONING_EFFORT)

            if CHATGPT_UNSUPPORTED_MODEL_ERROR in message.lower():
                raise RuntimeError(
                    f"Model '{requested_model}' is not supported by your current Codex login. "
                    f"Use '{DEFAULT_CODEX_MODEL}' or leave the model field blank."
                ) from exc

            raise
