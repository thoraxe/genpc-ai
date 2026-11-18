"""Anthropic (Claude) as the AI model service, with structured JSON output (system-overview.md, LLM_PROVIDER)."""

from __future__ import annotations

import logging
import time

import anthropic

from .llm import LLMResult

log = logging.getLogger("dialog")


class AnthropicLLM:
    def __init__(
        self,
        model: str,
        api_key: str,
        schema: dict | None = None,
        effort: str | None = "low",
        timeout: float = 20.0,
        max_tokens: int = 2000,
    ):
        self.name = f"{model}@anthropic"
        self.model = model
        self.schema = schema
        self.effort = effort
        self.max_tokens = max_tokens  # room for adaptive thinking plus the short JSON reply
        self.client = anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=0)

    def complete_json(self, system: str, messages: list[dict]) -> LLMResult:
        output_config: dict = {}
        if self.effort:
            output_config["effort"] = self.effort
        if self.schema:
            output_config["format"] = {"type": "json_schema", "schema": self.schema}
        kw = {"output_config": output_config} if output_config else {}
        t0 = time.perf_counter()
        r = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=messages,
            **kw,
        )
        ms = (time.perf_counter() - t0) * 1000
        # A refusal or a cut-off reply has no valid JSON: the dialog engine then tries again or uses its fallback.
        if r.stop_reason not in ("end_turn", None):
            log.warning("Anthropic stop_reason: %s", r.stop_reason)
        text = next((b.text for b in r.content if b.type == "text"), "")
        return LLMResult(text=text, ms=ms, prompt_tokens=r.usage.input_tokens, completion_tokens=r.usage.output_tokens)
