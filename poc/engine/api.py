"""Game-neutral HTTP API. The web UI is just one client; a game mod would call the same routes.

Run: uv run uvicorn engine.api:app --app-dir poc --port 8000
"""

from __future__ import annotations

import math
import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from . import knowledge
from .dialog import DialogEngine
from .models import Fact, WorldEvent
from .providers import llm as llm_mod
from .providers import tts as tts_mod
from .store import Store, load_events, load_world

POC = Path(__file__).resolve().parents[1]
load_dotenv(POC.parent / ".env")
START_DAY = float(os.getenv("POC_START_DAY", "41"))
VAR = Path(os.getenv("POC_VAR_DIR", POC / "var"))
VAR.mkdir(parents=True, exist_ok=True)

world = load_world(POC / "data" / "world.json")
presets = load_events(POC / "data" / "events.json")
store = Store(os.getenv("POC_DB", VAR / "poc.db"), world, start_day=START_DAY)
CLOCK_EPS = 1e-6  # in days (~0.09 s): mod-side float jitter below this is "the same time"
lock = threading.Lock()  # one sqlite connection shared across request threads
_llm = None
tts = tts_mod.from_env()


def dialog() -> DialogEngine:
    global _llm
    if _llm is None:
        _llm = llm_mod.from_env()
    return DialogEngine(store, _llm)


app = FastAPI(title="NPC Knowledge Engine PoC")


# ---------- schemas ----------
class Advance(BaseModel):
    days: float


class ClockSet(BaseModel):
    day: float  # the game's current time, in in-game days


class EventIn(BaseModel):
    preset: str | None = None
    witnesses: list[str] | None = None
    # full form (what a game mod would send)
    type: str | None = None
    location: str | None = None
    facts: list[Fact] | None = None


class Open(BaseModel):
    npc_id: str


class Choose(BaseModel):
    npc_id: str
    session_id: int
    text: str


class SaveIn(BaseModel):
    label: str = ""


# ---------- helpers ----------
def npc_or_404(npc_id: str):
    n = next((n for n in world.npcs if n.id == npc_id), None)
    if not n:
        raise HTTPException(404, f"unknown npc {npc_id}")
    return n


def _mem_json(m):
    return {
        "id": m.id,
        "npc_id": m.npc_id,
        "source": m.source,
        "event_id": m.event_id,
        "created_day": m.created_day,
        "facts": [f.model_dump() for f in m.facts],
    }


# ---------- routes ----------
@app.get("/")
def index():
    return FileResponse(POC / "ui" / "index.html")


@app.post("/api/session/start")
def session_start():
    return {
        "protocol": 1,
        "capabilities": {"max_choices": 3, "free_text": True, "audio": tts.media_type if tts else None},
        "llm": _llm.name if _llm else os.getenv("LLM_MODEL", os.getenv("ZAI_MODEL", "glm-5.3-flash")),
        "tts": tts.name if tts else None,
    }


@app.get("/api/world")
def get_world():
    with lock:
        counts = {
            n.id: len(
                [
                    v
                    for v in (knowledge.view(m, store.day, world.rules) for m in store.memories(n.id))
                    if v.stage != "forgotten"
                ]
            )
            for n in world.npcs
        }
        return {
            "day": store.day,
            "settlements": [s.model_dump() for s in world.settlements],
            "locations": [loc.model_dump() for loc in world.locations],
            "npcs": [{**n.model_dump(exclude={"bio"}), "known": counts[n.id]} for n in world.npcs],
            "events": [e.model_dump() for e in store.events()],
            "presets": {
                k: {"label": v["label"], "default_witnesses": v["default_witnesses"]} for k, v in presets.items()
            },
            "saves": store.saves(),
            "rules": world.rules.model_dump(),
        }


@app.post("/api/clock/advance")
def advance(a: Advance):
    if a.days <= 0 or a.days > 365:
        raise HTTPException(400, "days must be in (0, 365]")
    with lock:
        new = store.advance(a.days)
        return {"day": store.day, "new_memories": [_mem_json(m) for m in new]}


@app.post("/api/clock/set")
def clock_set(c: ClockSet):
    """Sync to the game's clock. Forward only: going back in time is a save load, never a clock change."""
    if not math.isfinite(c.day):
        raise HTTPException(400, "day must be a finite number")
    with lock:
        if c.day < store.day - CLOCK_EPS:
            raise HTTPException(409, f"clock is at day {store.day!r}; it only moves forward (load a save to go back)")
        if c.day - store.day > 365:
            raise HTTPException(400, "a single clock jump may be at most 365 days")
        new = store.set_day(c.day) if c.day > store.day + CLOCK_EPS else []  # within EPS counts as the same time
        return {"day": store.day, "new_memories": [_mem_json(m) for m in new]}


@app.post("/api/events")
def report_event(e: EventIn):
    with lock:
        if e.preset:
            p = presets.get(e.preset)
            if not p:
                raise HTTPException(404, f"unknown preset {e.preset}")
            etype, loc, facts = p["type"], p["location"], [Fact(**f) for f in p["facts"]]
            witnesses = e.witnesses if e.witnesses is not None else p["default_witnesses"]
        else:
            if not (e.type and e.location and e.facts):
                raise HTTPException(400, "give a preset, or type + location + facts")
            etype, loc, facts, witnesses = e.type, e.location, e.facts, e.witnesses or []
        for w in witnesses:
            npc_or_404(w)
        ev = WorldEvent(
            id=f"{e.preset or etype}@{store.day:g}#{len(store.events()) + 1}",
            type=etype,
            location=loc,
            day=store.day,
            facts=facts,
            witnesses=witnesses,
        )
        new = store.report_event(ev)
        return {"event": ev.model_dump(), "new_memories": [_mem_json(m) for m in new]}


@app.post("/api/dialog/open")
def dialog_open(o: Open):
    npc_or_404(o.npc_id)
    with lock:
        return dialog().open(o.npc_id).model_dump()


@app.post("/api/dialog/choose")
def dialog_choose(c: Choose):
    npc_or_404(c.npc_id)
    if not c.text.strip() or len(c.text) > 500:
        raise HTTPException(400, "text must be 1-500 characters")
    with lock:
        return dialog().choose(c.session_id, c.npc_id, c.text.strip()).model_dump()


@app.get("/api/audio/{turn_id}")
def audio(turn_id: int):
    if not tts:
        raise HTTPException(404, "TTS disabled (set ELEVENLABS_API_KEY, TTS_ENABLED=1)")
    with lock:
        t = store.turn(turn_id)
    if not t:
        raise HTTPException(404, "unknown turn")
    npc = npc_or_404(t["npc_id"])
    if not npc.voice_id:
        raise HTTPException(404, "npc has no voice")
    return StreamingResponse(tts.stream(t["npc_line"], npc.voice_id), media_type=tts.media_type)


@app.get("/api/npc/{npc_id}/knowledge")
def npc_knowledge(npc_id: str):
    npc = npc_or_404(npc_id)
    with lock:
        events = {e.id: e for e in store.events()}
        out = []
        for m in store.memories(npc_id):
            v = knowledge.view(m, store.day, world.rules)
            lost = []
            if m.event_id and m.event_id in events:  # facts that never survived the retelling
                have = {f.text for f in m.facts}
                lost = [f.model_dump() for f in events[m.event_id].facts if f.text not in have]
            out.append(
                {
                    **_mem_json(m),
                    "salience": m.salience,
                    "recalls": m.recalls,
                    "mentioned": m.mentioned,
                    "strength": round(v.strength, 4),
                    "stage": v.stage,
                    "kept": [f.model_dump() for f in v.kept_facts],
                    "faded": [f.model_dump() for f in v.dropped_facts],
                    "lost_in_retelling": lost,
                }
            )
        out.sort(key=lambda x: x["strength"], reverse=True)
        return {"npc": npc.model_dump(), "day": store.day, "memories": out, "turns": store.turns(npc_id, limit=12)}


@app.get("/api/npc/{npc_id}/prompt")
def npc_prompt(npc_id: str):
    npc_or_404(npc_id)
    with lock:
        return {"prompt": DialogEngine(store, None).preview_prompt(npc_id)}


@app.post("/api/saves")
def save(s: SaveIn):
    with lock:
        return {"id": store.save(s.label), "saves": store.saves()}


@app.post("/api/saves/{save_id}/load")
def load(save_id: int):
    with lock:
        try:
            store.load(save_id)
        except KeyError:
            raise HTTPException(404, "unknown save") from None
        return {"day": store.day}


@app.post("/api/reset")
def reset():
    with lock:
        store.reset(START_DAY)
        return {"day": store.day}
