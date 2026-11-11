"""Deterministic knowledge rules: witnessing, rumor hops, decay/gist, retrieval, grounding.

Pure functions; persistence lives in store.py. The LLM never decides what an NPC knows.
"""

from __future__ import annotations

import math
import re

from .models import NPC, Fact, Memory, MemoryView, Rules, WorldConfig, WorldEvent

# ---------- decay ----------


def strength(mem: Memory, now: float, rules: Rules) -> float:
    age = max(0.0, now - mem.created_day)
    boost = min(rules.recall_cap, rules.recall_boost * mem.recalls)
    return mem.salience * math.exp(-rules.decay_lambda * age) * (1 + boost)


def view(mem: Memory, now: float, rules: Rules) -> MemoryView:
    s = strength(mem, now, rules)
    if s < rules.forget_threshold:
        return MemoryView(memory=mem, strength=s, stage="forgotten", kept_facts=[], dropped_facts=list(mem.facts))
    if s < rules.gist_threshold:
        kept = [f for f in mem.facts if f.importance >= rules.gist_min_importance]
        dropped = [f for f in mem.facts if f.importance < rules.gist_min_importance]
        return MemoryView(memory=mem, strength=s, stage="gist", kept_facts=kept, dropped_facts=dropped)
    return MemoryView(memory=mem, strength=s, stage="detailed", kept_facts=list(mem.facts), dropped_facts=[])


# ---------- events and rumors ----------


def event_settlement(event: WorldEvent, world: WorldConfig) -> str:
    for loc in world.locations:
        if loc.id == event.location:
            return loc.near_settlement
    return event.location  # the event happened in a settlement itself


def witness_memories(event: WorldEvent) -> list[Memory]:
    return [
        Memory(
            npc_id=w,
            source="witnessed",
            event_id=event.id,
            created_day=event.day,
            salience=1.0,
            facts=list(event.facts),
        )
        for w in event.witnesses
    ]


def due_rumors(
    event: WorldEvent, world: WorldConfig, now: float, already_known: set[str], npcs: list[NPC] | None = None
) -> list[Memory]:
    """Rumor memories that should exist by `now` for NPCs who don't already know this event.

    `npcs` is every known NPC: the world-file NPCs plus the added NPCs (default: the world-file NPCs).
    An event whose town is not in the world file makes no gossip (knowledge.md rules 5a, 5d).

    Hop 1: NPCs in the event's settlement, after hop1_delay, facts >= hop1_min_importance.
    Hop 2: NPCs in settlements adjacent to it, after hop2_delay, facts >= hop2_min_importance.
    Nothing travels further. Arrival time (not `now`) is the memory's creation day.
    """
    r = world.rules
    home = event_settlement(event, world)
    town = next((s for s in world.settlements if s.id == home), None)
    if town is None:
        return []
    adjacent = town.adjacent
    npcs = world.npcs if npcs is None else npcs
    out: list[Memory] = []

    def add(npcs: list[NPC], source: str, delay: float, min_imp: int, sal: float):
        arrive = event.day + delay
        if now < arrive:
            return
        facts = [f for f in event.facts if f.importance >= min_imp]
        if not facts:
            return
        for n in npcs:
            if n.id in already_known:
                continue
            out.append(
                Memory(npc_id=n.id, source=source, event_id=event.id, created_day=arrive, salience=sal, facts=facts)
            )
            already_known.add(n.id)

    add(
        [n for n in npcs if n.settlement == home],
        "hop1",
        r.hop1_delay_days,
        r.hop1_min_importance,
        r.hop1_salience,
    )
    add(
        [n for n in npcs if n.settlement in adjacent],
        "hop2",
        r.hop2_delay_days,
        r.hop2_min_importance,
        r.hop2_salience,
    )
    return out


# ---------- retrieval ----------


def retrieve(memories: list[Memory], now: float, rules: Rules) -> list[MemoryView]:
    """Top-k non-forgotten memories by strength, plus a guaranteed 'recent news' slot:
    up to news_slots event memories younger than news_window_days not yet told to the player."""
    views = [v for v in (view(m, now, rules) for m in memories) if v.stage != "forgotten"]
    views.sort(key=lambda v: v.strength, reverse=True)
    news = [
        v
        for v in views
        if v.memory.event_id and not v.memory.mentioned and now - v.memory.created_day < rules.news_window_days
    ][: rules.news_slots]
    picked = news + [v for v in views if v not in news]
    return picked[: max(rules.retrieval_k, len(news))]


# ---------- grounding (for LLM-proposed conversation facts) ----------

_STOP = set(
    """the a an and or but if of to in on at for with from by about into over after before this that these those
is are was were be been being have has had do does did will would could should may might can just very really your yours
you i me my mine we our they them their he she him her his it its what which who whom whose when where why how not no yes
told tell said says say player""".split()
)


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) >= 4 and w not in _STOP}


def grounded(fact_text: str, transcript: str, min_ratio: float = 0.5) -> bool:
    """Keep a proposed fact only if at least half of its key terms appear in the conversation."""
    terms = _terms(fact_text)
    if not terms:
        return False
    have = _terms(transcript)
    return len(terms & have) / len(terms) >= min_ratio


def conversation_memory(npc_id: str, facts: list[Fact], day: float, transcript: str) -> Memory | None:
    kept = [f for f in facts if grounded(f.text, transcript)]
    if not kept:
        return None
    return Memory(npc_id=npc_id, source="conversation", created_day=day, salience=1.0, facts=kept)
