"""SQLite persistence plus save slots (whole-state snapshots, standing in for game saves)."""

from __future__ import annotations

import json
import math
import sqlite3
import time
from pathlib import Path

from . import knowledge
from .models import Memory, WorldConfig, WorldEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT, npc_id TEXT NOT NULL, event_id TEXT, body TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS mem_npc ON memories(npc_id);
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT, npc_id TEXT NOT NULL, day REAL NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS saves (
  id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, day REAL, created REAL, blob TEXT NOT NULL);
"""
STATE_TABLES = ("meta", "events", "memories", "turns")


class Store:
    def __init__(self, path: str | Path, world: WorldConfig, start_day: float = 0.0):
        self.world = world
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        if self._meta("day") is None:
            self._set_meta("day", start_day)
            self.db.commit()

    # ----- clock -----
    def _meta(self, k):
        row = self.db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return json.loads(row["v"]) if row else None

    def _set_meta(self, k, v):
        self.db.execute("INSERT OR REPLACE INTO meta(k,v) VALUES(?,?)", (k, json.dumps(v)))

    @property
    def day(self) -> float:
        return float(self._meta("day"))

    def advance(self, days: float) -> list[Memory]:
        if not math.isfinite(days):
            raise ValueError("days must be a real number")
        if days < 0:
            raise ValueError("time only moves forward; load a save to go back")
        self._set_meta("day", self.day + days)
        new = self.propagate()
        self.db.commit()
        return new

    # ----- events -----
    def report_event(self, event: WorldEvent) -> list[Memory]:
        if self.db.execute("SELECT 1 FROM events WHERE id=?", (event.id,)).fetchone():
            return []  # idempotent
        self.db.execute("INSERT INTO events(id, body) VALUES(?,?)", (event.id, event.model_dump_json()))
        known = self._knowers(event.id)
        mems = [m for m in knowledge.witness_memories(event) if m.npc_id not in known]
        for m in mems:
            self._add_memory(m)
        new = mems + self.propagate()
        self.db.commit()
        return new

    def events(self) -> list[WorldEvent]:
        return [WorldEvent.model_validate_json(r["body"]) for r in self.db.execute("SELECT body FROM events")]

    def propagate(self) -> list[Memory]:
        new: list[Memory] = []
        for ev in self.events():
            for m in knowledge.due_rumors(ev, self.world, self.day, self._knowers(ev.id)):
                self._add_memory(m)
                new.append(m)
        return new

    def _knowers(self, event_id: str) -> set[str]:
        return {r["npc_id"] for r in self.db.execute("SELECT npc_id FROM memories WHERE event_id=?", (event_id,))}

    # ----- memories -----
    def _add_memory(self, m: Memory) -> Memory:
        cur = self.db.execute(
            "INSERT INTO memories(npc_id, event_id, body) VALUES(?,?,?)",
            (m.npc_id, m.event_id, m.model_dump_json(exclude={"id"})),
        )
        m.id = cur.lastrowid
        return m

    def add_memory(self, m: Memory) -> Memory:
        m = self._add_memory(m)
        self.db.commit()
        return m

    def memories(self, npc_id: str) -> list[Memory]:
        out = []
        for r in self.db.execute("SELECT id, body FROM memories WHERE npc_id=? ORDER BY id", (npc_id,)):
            m = Memory.model_validate_json(r["body"])
            m.id = r["id"]
            out.append(m)
        return out

    def update_memory(self, m: Memory) -> None:
        self.db.execute("UPDATE memories SET body=? WHERE id=?", (m.model_dump_json(exclude={"id"}), m.id))

    def mark_used(self, used: list[Memory], mentioned_ids: set[int]) -> None:
        """After a delivered turn: each retrieved memory counts as a recall; news items shown get marked."""
        for m in used:
            m.recalls += 1
            if m.id in mentioned_ids:
                m.mentioned = True
            self.update_memory(m)
        self.db.commit()

    # ----- conversation turns -----
    def add_turn(self, npc_id: str, body: dict) -> int:
        cur = self.db.execute(
            "INSERT INTO turns(npc_id, day, body) VALUES(?,?,?)", (npc_id, self.day, json.dumps(body))
        )
        self.db.commit()
        return cur.lastrowid

    def turn(self, turn_id: int) -> dict | None:
        r = self.db.execute("SELECT id, npc_id, day, body FROM turns WHERE id=?", (turn_id,)).fetchone()
        return {"id": r["id"], "npc_id": r["npc_id"], "day": r["day"], **json.loads(r["body"])} if r else None

    def reset(self, start_day: float) -> None:
        """Wipe world state (keeps save slots, like deleting progress but not the save folder)."""
        for t in STATE_TABLES:
            self.db.execute(f"DELETE FROM {t}")
        self._set_meta("day", start_day)
        self.db.commit()

    def turns(self, npc_id: str, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, day, body FROM turns WHERE npc_id=? ORDER BY id DESC LIMIT ?", (npc_id, limit)
        ).fetchall()
        return [{"id": r["id"], "day": r["day"], **json.loads(r["body"])} for r in reversed(rows)]

    # ----- save slots -----
    def save(self, label: str = "") -> int:
        blob = {t: [dict(r) for r in self.db.execute(f"SELECT * FROM {t}")] for t in STATE_TABLES}
        cur = self.db.execute(
            "INSERT INTO saves(label, day, created, blob) VALUES(?,?,?,?)",
            (label or f"Day {self.day:g}", self.day, time.time(), json.dumps(blob)),
        )
        self.db.commit()
        return cur.lastrowid

    def load(self, save_id: int) -> None:
        row = self.db.execute("SELECT blob FROM saves WHERE id=?", (save_id,)).fetchone()
        if not row:
            raise KeyError(save_id)
        blob = json.loads(row["blob"])
        for t in STATE_TABLES:
            self.db.execute(f"DELETE FROM {t}")
            for r in blob[t]:
                cols = ",".join(r)
                self.db.execute(f"INSERT INTO {t}({cols}) VALUES({','.join('?' * len(r))})", tuple(r.values()))
        self.db.commit()

    def saves(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT id, label, day, created FROM saves ORDER BY id")]


def load_world(path: str | Path) -> WorldConfig:
    return WorldConfig.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_events(path: str | Path) -> dict[str, dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
