"""Deterministic scenario tests (no network). Acceptance checks 1-4 from poc-python-ui-plan.md."""

from pathlib import Path

import pytest

from engine import knowledge
from engine.models import Fact, WorldEvent
from engine.store import Store, load_events, load_world

DATA = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "t.db", load_world(DATA / "world.json"), start_day=41.0)


def embershard(day=41.0):
    e = load_events(DATA / "events.json")["embershard_cleared"]
    return WorldEvent(
        id="ev1",
        type=e["type"],
        location=e["location"],
        day=day,
        facts=[Fact(**f) for f in e["facts"]],
        witnesses=e["default_witnesses"],
    )


def facts_of(store, npc):
    return {f.importance for m in store.memories(npc) if m.event_id == "ev1" for f in m.facts}


def test_witness_gets_everything(store):
    store.report_event(embershard())
    assert facts_of(store, "hrolf") == {1, 2, 3, 4, 5}
    (m,) = store.memories("hrolf")
    assert m.source == "witnessed" and m.salience == 1.0


def test_hop1_same_settlement_after_half_day(store):
    store.report_event(embershard())
    store.advance(0.4)
    assert facts_of(store, "torvald") == set()
    store.advance(0.1)
    assert facts_of(store, "torvald") == {3, 4, 5}
    (m,) = store.memories("torvald")
    assert m.source == "hop1" and m.salience == 0.8 and m.created_day == 41.5


def test_hop2_adjacent_settlement_is_vaguer(store):
    store.report_event(embershard())
    store.advance(2.9)
    assert facts_of(store, "eirik") == set()
    store.advance(0.1)  # day 44
    assert facts_of(store, "eirik") == {4, 5}  # no loot (3), no axe (2), no dusk (1)
    (m,) = store.memories("eirik")
    assert m.source == "hop2" and m.created_day == 44.0


def test_far_settlement_never_hears(store):
    store.report_event(embershard())
    store.advance(30)
    assert store.memories("sabine") == []


def test_time_jump_uses_arrival_time_not_now(store):
    store.report_event(embershard())
    store.advance(10)  # one big jump: both hops delivered, dated at their arrival
    assert store.memories("torvald")[0].created_day == 41.5
    assert store.memories("eirik")[0].created_day == 44.0


def test_report_is_idempotent(store):
    store.report_event(embershard())
    store.report_event(embershard())
    assert len(store.memories("hrolf")) == 1


def test_conversation_decay_detail_then_gist_then_forgotten(store):
    r = store.world.rules
    transcript = "Player: I'm hunting the dragon at Bleak Falls Barrow. My sister Lydia is sick in Falkreath."
    mem = knowledge.conversation_memory(
        "torvald",
        [
            Fact(text="The player is hunting a dragon at Bleak Falls Barrow", importance=4),
            Fact(text="The player's sister Lydia is sick in Falkreath", importance=2),
        ],
        day=10.0,
        transcript=transcript,
    )
    assert mem is not None and len(mem.facts) == 2

    v3 = knowledge.view(mem, 13.0, r)
    assert v3.stage == "detailed" and len(v3.kept_facts) == 2
    v30 = knowledge.view(mem, 40.0, r)
    assert v30.stage == "gist"
    assert [f.importance for f in v30.kept_facts] == [4] and [f.importance for f in v30.dropped_facts] == [2]
    assert knowledge.view(mem, 48.0, r).stage == "forgotten"  # ~37.4 days without recall


def test_recall_boost_is_capped(store):
    r = store.world.rules
    mem = knowledge.Memory(
        npc_id="x", source="conversation", created_day=0, salience=1.0, facts=[Fact(text="a", importance=3)], recalls=99
    )
    assert knowledge.strength(mem, 0, r) == pytest.approx(1.5)
    assert knowledge.view(mem, 30, r).stage == "gist"  # boosted 0.136
    assert knowledge.view(mem, 43, r).stage == "forgotten"  # boosted ~0.048


def test_save_then_load_rolls_back_knowledge(store):
    store.report_event(embershard())
    slot = store.save("before gossip")
    store.advance(3)
    assert facts_of(store, "eirik") == {4, 5}
    store.load(slot)
    assert store.day == 41.0
    assert store.memories("eirik") == [] and store.memories("torvald") == []
    store.advance(3)  # replaying the timeline re-derives the same rumors
    assert facts_of(store, "eirik") == {4, 5}


def test_grounding_rejects_invented_facts():
    transcript = "Player: I cleared the bandits out of the mine. Torvald: Good riddance."
    assert knowledge.grounded("The player cleared the bandits from the mine", transcript)
    assert not knowledge.grounded("The player is secretly the Dragonborn of legend", transcript)
    assert (
        knowledge.conversation_memory(
            "torvald", [Fact(text="The player owns a castle in Morthal", importance=3)], 1.0, transcript
        )
        is None
    )


def test_retrieval_guarantees_recent_news_and_mention_marking(store):
    r = store.world.rules
    # bury the rumor under several strong conversation memories
    for i in range(6):
        store.add_memory(
            knowledge.Memory(
                npc_id="torvald",
                source="conversation",
                created_day=41.4,
                salience=1.0,
                facts=[Fact(text=f"chat {i}", importance=3)],
            )
        )
    store.report_event(embershard())
    store.advance(0.5)
    picked = knowledge.retrieve(store.memories("torvald"), store.day, r)
    assert len(picked) == r.retrieval_k
    assert picked[0].memory.event_id == "ev1"  # news slot first despite lower strength
    rumor = picked[0].memory
    store.mark_used([v.memory for v in picked], {rumor.id})
    again = knowledge.retrieve(store.memories("torvald"), store.day, r)
    assert all(not (v.memory.event_id and not v.memory.mentioned) for v in again)
    assert next(m for m in store.memories("torvald") if m.id == rumor.id).recalls == 1


def test_store_refuses_a_non_number_advance(store):
    with pytest.raises(ValueError):
        store.advance(float("nan"))
    assert store.day == 41.0
