"""Dialog turns: retrieve knowledge -> build prompt -> LLM (JSON) -> validate -> write back memory.

The prompt contains ONLY the NPC's bio and the facts the engine retrieved for that NPC,
so an NPC cannot mention an event the knowledge model didn't give it.
"""
from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, ValidationError, field_validator

from . import knowledge
from .models import Fact, MemoryView, NPC
from .providers.llm import LLMProvider
from .store import Store

log = logging.getLogger("dialog")

SOURCE_FRAMING = {
    "witnessed": "you saw this yourself",
    "hop1": "you heard this from someone in town",
    "hop2": "a rumor travelers brought from nearby",
    "conversation": "the player told you this",
}
FALLBACK = {
    "npc_line": "Hm. Sorry, friend, I lost my train of thought.",
    "choices": ["What's the news around here?", "How are things with you?", "Goodbye."],
    "remember": [],
}


class RememberItem(BaseModel):
    fact: str
    importance: int = Field(ge=1, le=5)


class DialogResponse(BaseModel):
    npc_line: str = Field(min_length=1, max_length=600)
    choices: list[str]
    remember: list[RememberItem] = []

    @field_validator("choices")
    @classmethod
    def three_choices(cls, v: list[str]) -> list[str]:
        v = [c.strip() for c in v if isinstance(c, str) and c.strip()]
        if len(v) < 3:
            raise ValueError("need at least 3 choices")
        return v[:3]


class TurnResult(BaseModel):
    turn_id: int
    session_id: int
    npc_id: str
    npc_line: str
    choices: list[str]
    remembered: list[Fact] = []
    rejected: list[str] = []
    used_memory_ids: list[int] = []
    llm_ms: float | None = None
    attempts: int = 0
    fallback: bool = False
    sent: dict | None = None  # exactly what went to the LLM on the last attempt: {system, messages}
    raw_reply: str | None = None  # the LLM's raw text on the last attempt


def _knowledge_block(views: list[MemoryView], now: float, rules) -> str:
    if not views:
        return "(You know nothing notable beyond everyday life in your town.)"
    lines = []
    for v in views:
        m = v.memory
        ago = now - m.created_day
        when = "today" if ago < 1 else f"about {round(ago)} day{'s' if round(ago) != 1 else ''} ago"
        clarity = " You only vaguely remember the gist." if v.stage == "gist" else ""
        news = (" [RECENT NEWS: bring this up naturally if you haven't told the player]"
                if m.event_id and not m.mentioned and ago < rules.news_window_days else "")
        facts = "; ".join(f.text for f in v.kept_facts)
        lines.append(f"- ({SOURCE_FRAMING[m.source]}, {when}.{clarity}){news} {facts}")
    return "\n".join(lines)


def build_system_prompt(npc: NPC, settlement_name: str, views: list[MemoryView], day: float, rules) -> str:
    return f"""You are {npc.name}, a {npc.role} in {settlement_name}. {npc.bio}

It is in-game day {day:g}. Stay in character and speak like a person from a medieval fantasy village.

WHAT YOU KNOW (this is your ENTIRE knowledge of recent events and of the player):
{_knowledge_block(views, day, rules)}

RULES:
- Mention only events listed above. Never invent news, events, quests, names or places that are not listed.
- If the player asks about something not listed, you don't know about it; say so in character.
- Secondhand or vague knowledge must sound uncertain ("they say", "I heard"). Don't add details that aren't listed.
- npc_line: 1-2 short spoken sentences, no stage directions or narration.
- choices: exactly 3 short things the player could say next (under 12 words each); make one of them a way to leave.
- remember: facts the PLAYER revealed about themselves in their latest line that you'd remember (empty list if none),
  each with importance 1-5.

Reply with JSON only: {{"npc_line": "...", "choices": ["...", "...", "..."], "remember": [{{"fact": "...", "importance": 3}}]}}"""


GREETING = "(The player walks up to you and you greet them.)"


def _history_messages(turns: list[dict]) -> list[dict]:
    msgs = []
    for t in turns:
        msgs.append({"role": "user", "content": t.get("player") or GREETING})
        msgs.append({"role": "assistant", "content": json.dumps({"npc_line": t["npc_line"], "choices": t["choices"]})})
    return msgs


class DialogEngine:
    def __init__(self, store: Store, llm: LLMProvider):
        self.store = store
        self.llm = llm

    def npc(self, npc_id: str) -> NPC:
        for n in self.store.world.npcs:
            if n.id == npc_id:
                return n
        raise KeyError(npc_id)

    def preview_prompt(self, npc_id: str) -> str:
        npc = self.npc(npc_id)
        views = knowledge.retrieve(self.store.memories(npc_id), self.store.day, self.store.world.rules)
        return build_system_prompt(npc, self._settlement(npc), views, self.store.day, self.store.world.rules)

    def _settlement(self, npc: NPC) -> str:
        return next((s.name for s in self.store.world.settlements if s.id == npc.settlement), npc.settlement)

    def open(self, npc_id: str) -> TurnResult:
        return self._turn(npc_id, session_id=None, player_text=None)

    def choose(self, session_id: int, npc_id: str, player_text: str) -> TurnResult:
        return self._turn(npc_id, session_id=session_id, player_text=player_text)

    def _turn(self, npc_id: str, session_id: int | None, player_text: str | None) -> TurnResult:
        store, rules = self.store, self.store.world.rules
        npc = self.npc(npc_id)
        views = knowledge.retrieve(store.memories(npc_id), store.day, rules)
        system = build_system_prompt(npc, self._settlement(npc), views, store.day, rules)
        session = [t for t in store.turns(npc_id) if session_id is not None and t.get("session_id") == session_id]
        messages = _history_messages(session)
        messages.append({"role": "user", "content": player_text or GREETING})

        resp, attempts, total_ms, fallback, sent, raw = None, 0, 0.0, False, None, None
        for attempt in range(2):
            attempts += 1
            sent, raw = {"system": system, "messages": messages}, None
            try:
                r = self.llm.complete_json(system, messages)
                total_ms += r.ms
                raw = r.text
                resp = DialogResponse.model_validate(json.loads(r.text))
                break
            except (json.JSONDecodeError, ValidationError) as e:
                log.warning("invalid LLM JSON (attempt %d): %s", attempt + 1, str(e)[:200])
                messages = messages + [{"role": "user", "content": "That was not valid JSON in the required format. Reply again with JSON only."}]
            except Exception as e:  # network / provider error: don't retry, use fallback
                log.warning("LLM call failed: %s", str(e)[:200])
                break
        if resp is None:
            resp, fallback = DialogResponse.model_validate(FALLBACK), True

        # memory write-back: only facts grounded in what the player actually said this session
        remembered: list[Fact] = []
        rejected: list[str] = []
        if player_text and resp.remember:
            player_lines = " ".join([t["player"] for t in session if t.get("player")] + [player_text])
            mem = knowledge.conversation_memory(
                npc_id, [Fact(text=i.fact, importance=i.importance) for i in resp.remember], store.day, player_lines)
            remembered = mem.facts if mem else []
            rejected = [i.fact for i in resp.remember if i.fact not in {f.text for f in remembered}]
            if mem:
                store.add_memory(mem)

        if not fallback:  # a delivered turn counts as recall; news counts as told only if the line says it
            news_ids = {v.memory.id for v in views
                        if v.memory.event_id and not v.memory.mentioned
                        and store.day - v.memory.created_day < rules.news_window_days
                        and any(knowledge.grounded(f.text, resp.npc_line) for f in v.kept_facts)}
            store.mark_used([v.memory for v in views], news_ids)

        body = {"session_id": session_id, "player": player_text, "npc_line": resp.npc_line, "choices": resp.choices}
        turn_id = store.add_turn(npc_id, body)
        if session_id is None:  # first turn of a conversation defines the session
            session_id = turn_id
            body["session_id"] = session_id
            store.db.execute("UPDATE turns SET body=? WHERE id=?", (json.dumps(body), turn_id))
            store.db.commit()

        return TurnResult(turn_id=turn_id, session_id=session_id, npc_id=npc_id, npc_line=resp.npc_line,
                          choices=resp.choices, remembered=remembered, rejected=rejected,
                          used_memory_ids=[v.memory.id for v in views], llm_ms=total_ms or None,
                          attempts=attempts, fallback=fallback, sent=sent, raw_reply=raw)
