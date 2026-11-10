"""LLM provider interface + an OpenAI-compatible implementation (z.ai by default).

Swapping to OpenRouter or another OpenAI-compatible API is config only:
LLM_BASE_URL / LLM_MODEL / LLM_API_KEY_ENV.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI


@dataclass
class LLMResult:
    text: str
    ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(Protocol):
    name: str

    def complete_json(self, system: str, messages: list[dict]) -> LLMResult: ...


class OpenAICompatLLM:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        reasoning_effort: str | None = "low",
        timeout: float = 20.0,
        max_tokens: int = 500,
    ):
        self.name = f"{model}@{base_url}"
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)

    def complete_json(self, system: str, messages: list[dict]) -> LLMResult:
        import time

        kw = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        t0 = time.perf_counter()
        r = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, *messages],
            response_format={"type": "json_object"},
            max_tokens=self.max_tokens,
            **kw,
        )
        ms = (time.perf_counter() - t0) * 1000
        u = r.usage
        return LLMResult(
            text=r.choices[0].message.content or "",
            ms=ms,
            prompt_tokens=u and u.prompt_tokens,
            completion_tokens=u and u.completion_tokens,
        )


def from_env() -> OpenAICompatLLM:
    key_env = os.getenv("LLM_API_KEY_ENV", "ZAI_API_KEY")
    key = os.getenv(key_env)
    if not key:
        raise RuntimeError(f"{key_env} is not set (see .env)")
    return OpenAICompatLLM(
        base_url=os.getenv("LLM_BASE_URL", os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4/")),
        model=os.getenv("LLM_MODEL", os.getenv("ZAI_MODEL", "glm-5.3-flash")),
        api_key=key,
        reasoning_effort=os.getenv("LLM_REASONING_EFFORT", "low") or None,
    )
