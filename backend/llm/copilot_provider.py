"""GitHub Copilot CLI-backed LLM provider."""
import asyncio
import shutil
from time import perf_counter

from backend.logging_utils import log_event
from .cli_base import CLIProvider


class CopilotProvider(CLIProvider):
    """Use the local GitHub Copilot CLI as the model backend."""

    def __init__(self, model: str | None = "gpt-4.1"):
        super().__init__(model=model)
        self.command = self._detect_command()

    @staticmethod
    def _detect_command() -> list[str]:
        if shutil.which("copilot"):
            return ["copilot"]
        if shutil.which("gh"):
            return ["gh", "copilot"]
        raise ValueError("GitHub Copilot CLI is not available. Install `copilot` or `gh copilot` first.")

    async def _run_prompt(self, prompt: str) -> str:
        stage_started = perf_counter()
        log_event("llm", "COPILOT", f"dispatching request | model={self.model or 'default'}")
        cmd = [*self.command]
        if self.model:
            cmd.extend(["--model", self.model])
        cmd.extend(["-p", prompt])
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode("utf-8", errors="ignore").strip()
        stderr_text = stderr.decode("utf-8", errors="ignore").strip()

        if process.returncode != 0:
            unsupported_model_flag = any(
                marker in stderr_text.lower()
                for marker in ("unknown option", "unknown flag", "unrecognized option", "unexpected argument '--model'")
            )
            if self.model and unsupported_model_flag:
                log_event("llm", "COPILOT", "local CLI does not accept --model, retrying with local default")
                retry_process = await asyncio.create_subprocess_exec(
                    *self.command,
                    "-p",
                    prompt,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                retry_stdout, retry_stderr = await retry_process.communicate()
                retry_stdout_text = retry_stdout.decode("utf-8", errors="ignore").strip()
                retry_stderr_text = retry_stderr.decode("utf-8", errors="ignore").strip()
                if retry_process.returncode == 0 and retry_stdout_text:
                    log_event("llm", "COPILOT", f"response received in {perf_counter() - stage_started:.2f}s")
                    return retry_stdout_text
                raise RuntimeError(
                    retry_stderr_text
                    or retry_stdout_text
                    or "GitHub Copilot CLI exited with a non-zero status."
                )

            raise RuntimeError(
                stderr_text
                or stdout_text
                or "GitHub Copilot CLI exited with a non-zero status."
            )

        if stdout_text:
            log_event("llm", "COPILOT", f"response received in {perf_counter() - stage_started:.2f}s")
            return stdout_text

        raise RuntimeError("GitHub Copilot CLI returned an empty response.")
