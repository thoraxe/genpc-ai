"""Game-neutral HTTP API. The web UI is just one client; a game mod would call the same routes.

Run: uv run uvicorn engine.api:app --app-dir poc --port 8000
"""

from __future__ import annotations

import hashlib
import math
import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, ValidationError

from . import knowledge
from .dialog import DialogEngine
from .models import Fact, WorldConfig, WorldEvent, world_problems
from .providers import llm as llm_mod
from .providers import tts as tts_mod
from .store import Store, load_events, load_world

POC = Path(__file__).resolve().parents[1]
load_dotenv(POC.parent / ".env")
START_DAY = float(os.getenv("POC_START_DAY", "41"))
VAR = Path(os.getenv("POC_VAR_DIR", POC / "var"))
VAR.mkdir(parents=True, exist_ok=True)

TEST_WORLD_ID = "test"  # the built-in test world; a mod cannot use this name
TEST_DB = Path(os.getenv("POC_DB", VAR / "poc.db"))


def _start_day(w: WorldConfig) -> float:
    return w.start_day if w.start_day is not None else START_DAY


def _db_path(world_id: str) -> Path:
    """Each world keeps its knowledge in its own database file (world-file.md rule 16d).

    The file name is a hash of the world id, so a mod's id can never become a path."""
    if world_id == TEST_WORLD_ID:
        return TEST_DB
    return VAR / f"world-{hashlib.sha256(world_id.encode()).hexdigest()[:16]}.db"


world = load_world(POC / "data" / "world.json")
presets = load_events(POC / "data" / "events.json")  # presets belong only to the test world
store = Store(_db_path(world.id), world, start_day=_start_day(world))
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
    hours: float  # hours since the game started; checked in clock_set


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
        "world": world.id,
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
            "world": world.id,
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


@app.post("/api/world")
def set_world(body: object = Body(None)):
    """A mod sends its own world (world-file.md rules 16-16s, http-api.md rules 8a-8d)."""
    global world, presets, store
    if not isinstance(body, dict):
        raise HTTPException(400, "world is not correct: the body must be a JSON object")
    try:
        w = WorldConfig.model_validate(body)
    except ValidationError as e:
        reasons = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:5])
        raise HTTPException(400, f"world is not correct: {reasons}") from None
    if w.id.casefold() == TEST_WORLD_ID:
        raise HTTPException(400, f"world is not correct: a mod cannot use the world name {TEST_WORLD_ID!r}")
    problems = world_problems(w)
    if problems:
        raise HTTPException(400, "world is not correct: " + "; ".join(problems))
    with lock:
        if store.world.id == w.id:
            store.world = w  # same world, maybe changed: memories stay (rules 16j-16k)
        else:  # open the new world first: if that fails, the world in use stays (rule 16m)
            new = Store(_db_path(w.id), w, start_day=_start_day(w))
            old, store = store, new
            old.db.close()
        world, presets = w, {}
    return {"world": w.id, "towns": len(w.settlements), "npcs": len(w.npcs)}


@app.exception_handler(RequestValidationError)
async def _bad_request_body(request: Request, exc: RequestValidationError):
    """A body that is not JSON: `/api/world` answers 400, not 422 (http-api.md rule 8d)."""
    if request.url.path == "/api/world":
        return JSONResponse(status_code=400, content={"detail": "world is not correct: the body is not valid JSON"})
    return await request_validation_exception_handler(request, exc)


@app.post("/api/clock/advance")
def advance(a: Advance):
    if a.days <= 0 or a.days > 365:
        raise HTTPException(400, "days must be in (0, 365]")
    with lock:
        new = store.advance(a.days)
        return {"day": store.day, "new_memories": [_mem_json(m) for m in new]}


@app.post("/api/clock/set")
def clock_set(c: ClockSet):
    """The game sets the clock from its hours (saves-and-clock.md rules 5a-5g, http-api.md rules 10a-10e)."""
    with lock:
        day = store.day

        def refuse(reason: str):
            raise HTTPException(400, {"error": reason, "day": day})

        if not math.isfinite(c.hours) or c.hours < 0:
            refuse("hours must be a number, 0 or more")
        delta = c.hours / world.calendar.hours_per_day - day
        if abs(delta) < 1e-9:  # the same hours again: nothing changes
            return {"day": day, "new_memories": []}
        if delta < 0:
            refuse("the game's hours went back: load the save with the same name first")
        if delta > 365 + 1e-9:
            refuse("a clock move can be a maximum of 365 days")
        new = store.advance(delta)
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
    with lock:
        npc_or_404(o.npc_id)
        return dialog().open(o.npc_id).model_dump()


@app.post("/api/dialog/choose")
def dialog_choose(c: Choose):
    if not c.text.strip() or len(c.text) > 500:
        raise HTTPException(400, "text must be 1-500 characters")
    with lock:
        npc_or_404(c.npc_id)
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
    with lock:
        npc = npc_or_404(npc_id)
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
    with lock:
        npc_or_404(npc_id)
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
        store.reset(_start_day(world))
        return {"day": store.day}
