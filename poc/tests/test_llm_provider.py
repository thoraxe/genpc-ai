"""LLM_PROVIDER (system-overview.md, Configuration Surface). No network."""

import json
from types import SimpleNamespace

import pytest

from engine.dialog import REPLY_SCHEMA, DialogResponse
from engine.providers import llm
from engine.providers.anthropic_llm import AnthropicLLM


@pytest.fixture
def no_llm_env(monkeypatch):
    for k in ("LLM_PROVIDER", "LLM_API_KEY_ENV", "LLM_MODEL", "LLM_BASE_URL", "LLM_REASONING_EFFORT", "ZAI_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "test-zai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    return monkeypatch


def test_default_is_openai_compatible(no_llm_env):
    # Example 2: without LLM_PROVIDER nothing changes.
    p = llm.from_env()
    assert isinstance(p, llm.OpenAICompatLLM) and p.model == "glm-5.3-flash"


def test_anthropic_uses_its_own_key_and_haiku(no_llm_env):
    # Example 1 and owner question 1: the tester's own key; Haiku 5.5 is the default model.
    no_llm_env.setenv("LLM_PROVIDER", "anthropic")
    no_llm_env.delenv("ZAI_API_KEY")
    p = llm.from_env()
    assert isinstance(p, AnthropicLLM) and p.model == "claude-haiku-5-5" and p.effort == "low"
    assert p.schema is REPLY_SCHEMA


def test_anthropic_model_can_change(no_llm_env):
    # Example 3.
    no_llm_env.setenv("LLM_PROVIDER", "Anthropic")
    no_llm_env.setenv("LLM_MODEL", "claude-opus-5-5")
    assert llm.from_env().model == "claude-opus-5-5"


def test_anthropic_without_key_says_so(no_llm_env):
    # Example 4.
    no_llm_env.setenv("LLM_PROVIDER", "anthropic")
    no_llm_env.delenv("ANTHROPIC_API_KEY")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is not set"):
        llm.from_env()


def test_unknown_provider_is_refused(no_llm_env):
    no_llm_env.setenv("LLM_PROVIDER", "other")
    with pytest.raises(RuntimeError, match="openai or anthropic"):
        llm.from_env()


class FakeMessages:
    def __init__(self, content):
        self.content = content
        self.kw = None

    def create(self, **kw):
        self.kw = kw
        return SimpleNamespace(
            stop_reason="end_turn", content=self.content, usage=SimpleNamespace(input_tokens=11, output_tokens=7)
        )


def test_anthropic_request_and_reply():
    reply = {"npc_line": "Well met.", "choices": ["a", "b", "Goodbye."], "remember": []}
    p = AnthropicLLM(model="claude-haiku-5-5", api_key="x", schema=REPLY_SCHEMA)
    fake = FakeMessages(
        [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=json.dumps(reply))]
    )
    p.client = SimpleNamespace(messages=fake)
    r = p.complete_json("SYSTEM", [{"role": "user", "content": "hi"}])
    assert DialogResponse.model_validate_json(r.text).npc_line == "Well met."
    assert (r.prompt_tokens, r.completion_tokens) == (11, 7)
    kw = fake.kw
    assert kw["system"] == "SYSTEM" and kw["messages"] == [{"role": "user", "content": "hi"}]
    assert kw["output_config"] == {"effort": "low", "format": {"type": "json_schema", "schema": REPLY_SCHEMA}}
    assert "temperature" not in kw and "thinking" not in kw


def test_anthropic_refusal_gives_empty_text():
    # No text block (for example a refusal): the dialog engine tries again or uses its fallback.
    p = AnthropicLLM(model="claude-haiku-5-5", api_key="x")
    p.client = SimpleNamespace(messages=FakeMessages([]))
    assert p.complete_json("S", [{"role": "user", "content": "hi"}]).text == ""


def test_anthropic_effort_is_checked(no_llm_env):
    # Code review: a wrong effort would give a 400 on every call; empty means "do not send".
    no_llm_env.setenv("LLM_PROVIDER", "anthropic")
    no_llm_env.setenv("LLM_REASONING_EFFORT", "minimal")
    with pytest.raises(RuntimeError, match="low, medium or high"):
        llm.from_env()
    no_llm_env.setenv("LLM_REASONING_EFFORT", "")
    p = llm.from_env()
    assert p.effort is None
    fake = FakeMessages([SimpleNamespace(type="text", text="{}")])
    p.client = SimpleNamespace(messages=fake)
    p.complete_json("S", [{"role": "user", "content": "hi"}])
    assert "effort" not in fake.kw["output_config"]


def test_anthropic_error_gives_the_fallback_line(tmp_path):
    # Code review: an API error (for example no credit) gives the fallback line, not a crash.
    from pathlib import Path

    from engine.dialog import FALLBACK, DialogEngine
    from engine.store import Store, load_world

    store = Store(tmp_path / "t.db", load_world(Path(__file__).parents[1] / "data" / "world.json"), start_day=41.0)

    class Broken:
        name = "broken"

        def complete_json(self, system, messages):
            raise RuntimeError("credit balance is too low")

    t = DialogEngine(store, Broken()).open("hrolf")
    assert t.fallback and t.npc_line == FALLBACK["npc_line"]
