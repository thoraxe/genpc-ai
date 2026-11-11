"""Core data models. Game-neutral: nothing here knows about Skyrim."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Source = Literal["witnessed", "hop1", "hop2", "conversation"]
Stage = Literal["detailed", "gist", "forgotten"]


class Fact(BaseModel):
    text: str
    importance: int = Field(ge=1, le=5)


class Rules(BaseModel):
    """All tunables (parent plan §1 pinned defaults)."""

    decay_lambda: float = 0.08
    recall_boost: float = 0.25
    recall_cap: float = 0.5
    gist_threshold: float = 0.35
    gist_min_importance: int = 3
    forget_threshold: float = 0.05
    hop1_delay_days: float = 0.5
    hop1_min_importance: int = 3
    hop1_salience: float = 0.8
    hop2_delay_days: float = 3.0
    hop2_min_importance: int = 4
    hop2_salience: float = 0.6
    retrieval_k: int = 5
    news_window_days: float = 3.0
    news_slots: int = 2


class Settlement(BaseModel):
    id: str
    name: str
    adjacent: list[str] = []


class Location(BaseModel):
    id: str
    name: str
    near_settlement: str


class NPC(BaseModel):
    id: str
    name: str
    role: str
    settlement: str
    bio: str
    voice_id: str | None = None


DEFAULT_GENERIC_BIO = "You are an ordinary person. You have no special story."  # world-file.md rule 7f


class VoicePool(BaseModel):
    """Voices for added NPCs (world-file.md rules 7a-7d)."""

    female: list[str] = []
    male: list[str] = []


class AddedNPC(BaseModel):
    """An NPC that a mod adds while the game runs (http-api.md rules 31-42)."""

    id: str  # the record ID for a named NPC, "crowd-<entity ID>" for a crowd NPC
    kind: Literal["named", "crowd"]
    name: str
    settlement: str
    role: str | None = None
    faction: str | None = None
    gender: Literal["female", "male"] | None = None


def pick_voice(pool: VoicePool, npc_id: str, gender: str | None) -> str | None:
    """The same NPC always gets the same voice (world-file.md rules 7b-7d)."""
    voices = pool.female if gender == "female" else pool.male if gender == "male" else []
    voices = voices or pool.female + pool.male  # no gender, or no voice for it: all voices (rules 7c, 7ca)
    if not voices:
        return None
    return voices[int(hashlib.sha256(npc_id.encode()).hexdigest(), 16) % len(voices)]


def _faction_sentence(faction: str) -> str:
    name = faction[4:] if faction.lower().startswith("the ") else faction
    return f"You belong to the {name}."


class Calendar(BaseModel):
    """How time works in a game (world-file.md rules 1a-1b)."""

    hours_per_day: float = Field(24.0, gt=0, allow_inf_nan=False)


class WorldConfig(BaseModel):
    id: str  # world name; each world keeps its own knowledge
    start_day: float | None = Field(None, allow_inf_nan=False)  # None = POC_START_DAY
    setting: str = ""  # world flavour and speech style for every NPC prompt
    calendar: Calendar = Calendar()
    generic_bio: str = ""  # the general description of each added NPC; empty = DEFAULT_GENERIC_BIO
    voice_pool: VoicePool = VoicePool()
    rules: Rules = Rules()
    settlements: list[Settlement]
    locations: list[Location] = []
    npcs: list[NPC]

    @field_validator("id")
    @classmethod
    def id_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("the world has no id")
        return v


def added_npc_view(world: WorldConfig, a: AddedNPC) -> NPC:
    """What the prompt and the voice use for an added NPC (conversation.md rules 6a-6d)."""
    bio = world.generic_bio.strip() or DEFAULT_GENERIC_BIO
    if a.faction:
        bio = f"{bio} {_faction_sentence(a.faction)}"
    return NPC(
        id=a.id,
        name=a.name,
        role=a.role or "local",
        settlement=a.settlement,
        bio=bio,
        voice_id=pick_voice(world.voice_pool, a.id, a.gender),
    )


def world_problems(world: WorldConfig) -> list[str]:
    """Reasons why a world is not correct (world-file.md rule 16n). Empty list = correct."""
    problems: list[str] = []
    if not world.settlements:
        problems.append("the world has no settlements")
    if not world.npcs:
        problems.append("the world has no npcs")
    for kind, items in (("settlement", world.settlements), ("location", world.locations), ("npc", world.npcs)):
        seen: set[str] = set()
        for item in items:
            if item.id in seen:
                problems.append(f"two {kind}s have the id {item.id!r}")
            seen.add(item.id)
    towns = {t.id for t in world.settlements}
    for t in world.settlements:
        for a in t.adjacent:
            if a not in towns:
                problems.append(f"settlement {t.id!r} lists an unknown next town {a!r}")
    for loc in world.locations:
        if loc.near_settlement not in towns:
            problems.append(f"location {loc.id!r} names an unknown town {loc.near_settlement!r}")
    for n in world.npcs:
        if n.settlement not in towns:
            problems.append(f"npc {n.id!r} names an unknown town {n.settlement!r}")
    return problems


class WorldEvent(BaseModel):
    id: str
    type: str  # opaque tag, e.g. "location_cleared"
    location: str  # Location id or Settlement id
    day: float
    facts: list[Fact]
    witnesses: list[str]


class Memory(BaseModel):
    id: int | None = None
    npc_id: str
    source: Source
    event_id: str | None = None
    created_day: float
    salience: float
    recalls: int = 0
    mentioned: bool = False  # has this NPC already told the player about it?
    facts: list[Fact]


class MemoryView(BaseModel):
    """A memory as seen at a given in-game time (what the inspector and the prompt use)."""

    memory: Memory
    strength: float
    stage: Stage
    kept_facts: list[Fact]
    dropped_facts: list[Fact]  # lost to gist (rumor-hop losses are never stored at all)
