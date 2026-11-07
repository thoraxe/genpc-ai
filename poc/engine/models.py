"""Core data models. Game-neutral: nothing here knows about Skyrim."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


class WorldConfig(BaseModel):
    rules: Rules = Rules()
    settlements: list[Settlement]
    locations: list[Location] = []
    npcs: list[NPC]


class WorldEvent(BaseModel):
    id: str
    type: str          # opaque tag, e.g. "location_cleared"
    location: str      # Location id or Settlement id
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
    mentioned: bool = False   # has this NPC already told the player about it?
    facts: list[Fact]


class MemoryView(BaseModel):
    """A memory as seen at a given in-game time (what the inspector and the prompt use)."""
    memory: Memory
    strength: float
    stage: Stage
    kept_facts: list[Fact]
    dropped_facts: list[Fact]   # lost to gist (rumor-hop losses are never stored at all)
