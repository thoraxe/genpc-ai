"""Dialog pipeline tests with a fake LLM (no network)."""

import json
from pathlib import Path

import pytest

from engine.dialog import DialogEngine
from engine.models import Fact, WorldEvent
from engine.providers.llm import LLMResult
from engine.store import Store, load_events, load_world

DATA = Path(__file__).resolve().parents[1] / "data"


class FakeLLM:
    name = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete_json(self, system, messages):
        self.calls.append((system, messages))
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return LLMResult(text=r if isinstance(r, str) else json.dumps(r), ms=5.0)


GOOD = {
    "npc_line": "Heard the bandits at Embershard Mine are dead. Was that you?",
    "choices": ["Yes.", "No.", "Goodbye."],
    "remember": [],
}
SMALLTALK = {"npc_line": "Halt. State your business.", "choices": ["Passing through.", "Trade.", "Goodbye."]}


def test_news_not_marked_if_npc_did_not_mention_it(store):
    DialogEngine(store, FakeLLM([SMALLTALK])).open("eirik")
    (m,) = [m for m in store.memories("eirik") if m.event_id]
    assert not m.mentioned and m.recalls == 1


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.db", load_world(DATA / "world.json"), start_day=41.0)
    e = load_events(DATA / "events.json")["embershard_cleared"]
    s.report_event(
        WorldEvent(
            id="ev1",
            type=e["type"],
            location=e["location"],
            day=41.0,
            facts=[Fact(**f) for f in e["facts"]],
            witnesses=e["default_witnesses"],
        )
    )
    s.advance(3)
    return s


def test_prompt_contains_only_that_npcs_knowledge(store):
    d = DialogEngine(store, FakeLLM([]))
    sabine, eirik, torvald = d.preview_prompt("sabine"), d.preview_prompt("eirik"), d.preview_prompt("torvald")
    assert "Embershard" not in sabine and "bandit" not in sabine.lower()
    assert "Embershard" in eirik and "loot" not in eirik and "axe" not in eirik and "dusk" not in eirik
    assert "loot" in torvald and "axe" not in torvald
    assert "rumor travelers brought" in eirik and "someone in town" in torvald


def test_retry_once_then_succeed(store):
    llm = FakeLLM(["not json", GOOD])
    t = DialogEngine(store, llm).open("torvald")
    assert t.attempts == 2 and not t.fallback and t.npc_line == GOOD["npc_line"]


def test_fallback_after_two_bad_replies_and_no_recall(store):
    llm = FakeLLM(["{}", {"npc_line": "hi", "choices": ["only one"]}])
    before = [m.recalls for m in store.memories("torvald")]
    t = DialogEngine(store, llm).open("torvald")
    assert t.fallback and len(t.choices) == 3
    assert [m.recalls for m in store.memories("torvald")] == before


def test_provider_error_falls_back_without_retry(store):
    llm = FakeLLM([TimeoutError("slow")])
    t = DialogEngine(store, llm).open("eirik")
    assert t.fallback and t.attempts == 1


def test_news_marked_after_delivery_and_session_history(store):
    llm = FakeLLM(
        [
            GOOD,
            {
                **GOOD,
                "remember": [
                    {"fact": "The player is named Erik and comes from Falkreath", "importance": 3},
                    {"fact": "The player is a famous dragon slayer", "importance": 5},
                ],
            },
        ]
    )
    d = DialogEngine(store, llm)
    t1 = d.open("eirik")
    assert all(m.mentioned for m in store.memories("eirik") if m.event_id)
    t2 = d.choose(t1.session_id, "eirik", "I'm Erik, from Falkreath.")
    assert t2.session_id == t1.session_id
    # second call carried the first exchange as history
    msgs = llm.calls[1][1]
    assert msgs[-1]["content"] == "I'm Erik, from Falkreath." and len(msgs) == 3
    assert [f.text for f in t2.remembered] == ["The player is named Erik and comes from Falkreath"]
    assert t2.rejected == ["The player is a famous dragon slayer"]
    assert any(m.source == "conversation" for m in store.memories("eirik"))
