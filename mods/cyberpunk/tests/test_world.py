"""The Cyberpunk world (mod spec what/world.md). Offline: the engine API with no LLM and no TTS.

The tests send the world and the presets to the engine the same way the mod will (engine http-api.md rules 8a, 13).
"""

import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engine.models import WorldConfig, world_problems

MOD = Path(__file__).resolve().parents[1]
WORLD = json.loads((MOD / "world.json").read_text(encoding="utf-8"))
PRESETS = json.loads((MOD / "events.json").read_text(encoding="utf-8"))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("POC_VAR_DIR", str(tmp_path))
    monkeypatch.setenv("POC_DB", str(tmp_path / "test-world.db"))
    monkeypatch.setenv("TTS_ENABLED", "0")
    import engine.api as api

    c = TestClient(importlib.reload(api).app)
    r = c.post("/api/world", json=WORLD)
    assert r.status_code == 200, r.text
    return c


def happen(client, preset, day):
    """Move the clock to `day`, then send the preset in the full form."""
    now = client.get("/api/world").json()["day"]
    if day > now:
        client.post("/api/clock/advance", json={"days": day - now})
    p = PRESETS[preset]
    r = client.post(
        "/api/events",
        json={"type": p["type"], "location": p["location"], "facts": p["facts"], "witnesses": p["default_witnesses"]},
    )
    assert r.status_code == 200, r.text


def at(client, day):
    now = client.get("/api/world").json()["day"]
    if day > now:
        client.post("/api/clock/advance", json={"days": day - now})


def facts(client, npc):
    return {f["text"] for m in client.get(f"/api/npc/{npc}/knowledge").json()["memories"] for f in m["facts"]}


# ---------- rules 1-15: the world itself ----------
def test_world_is_correct_and_has_the_approved_shape():
    w = WorldConfig.model_validate(WORLD)
    assert world_problems(w) == []
    assert w.id == "cyberpunk" and w.start_day == 0
    assert w.rules.hop2_delay_days == 1.0
    assert {t.id for t in w.settlements} == {
        "watson",
        "westbrook",
        "city_center",
        "heywood",
        "santo_domingo",
        "pacifica",
        "badlands",
    }
    assert "dogtown" not in {t.id for t in w.settlements}
    assert len(w.npcs) == 9 and all(n.voice_id is None for n in w.npcs)
    for t in w.settlements:  # each link is in both towns (rule 3)
        for a in t.adjacent:
            assert t.id in next(x for x in w.settlements if x.id == a).adjacent
    default_rules = WorldConfig(id="x", settlements=[], npcs=[]).rules
    assert w.rules.model_dump(exclude={"hop2_delay_days"}) == default_rules.model_dump(exclude={"hop2_delay_days"})


def test_the_engine_accepts_the_world_and_starts_at_day_0(client):
    w = client.get("/api/world").json()
    assert w["world"] == "cyberpunk" and w["day"] == 0
    assert len(w["settlements"]) == 7 and len(w["npcs"]) == 9


# ---------- Summary examples 1-4 and the preset 1 examples ----------
def test_preset_1_gig_in_northside(client):
    happen(client, "maelstrom_gig_northside", 41)
    assert len(facts(client, "regina_jones")) == 5
    at(client, 41.4)
    assert facts(client, "robert_wilson") == set() and facts(client, "cassius_ryder") == set()
    at(client, 41.5)
    three = {
        "The Maelstrom hideout in Northside is gone",
        "A solo merc did it alone",
        "The merc took a crate of military weapons",
    }
    assert facts(client, "robert_wilson") == three and facts(client, "cassius_ryder") == three
    at(client, 42)
    two = {"The Maelstrom hideout in Northside is gone", "A solo merc did it alone"}
    assert facts(client, "wakako_okada") == two and facts(client, "dino_dinovic") == two
    at(client, 60)
    for npc in ("padre", "el_capitan", "mr_hands", "dakota_smith"):
        assert facts(client, npc) == set(), npc


# ---------- Summary example 5: Dogtown is not in the world ----------
def test_event_in_dogtown_reaches_only_its_witnesses(client):
    at(client, 41)
    r = client.post(
        "/api/events",
        json={
            "type": "gig_completed",
            "location": "dogtown",
            "facts": [{"text": "A gig in Dogtown is done", "importance": 5}],
            "witnesses": ["mr_hands"],
        },
    )
    assert r.status_code == 200
    at(client, 60)
    assert facts(client, "mr_hands") == {"A gig in Dogtown is done"}
    assert all(facts(client, n["id"]) == set() for n in WORLD["npcs"] if n["id"] != "mr_hands")


# ---------- preset 2 and preset 3 examples ----------
def test_preset_2_police_fight_in_the_glen(client):
    happen(client, "police_fight_the_glen", 41)
    at(client, 42)
    two = {"A merc fought the police in The Glen", "Two police officers died"}
    for npc in ("dino_dinovic", "el_capitan", "mr_hands"):
        assert facts(client, npc) == two, npc
    at(client, 60)
    for npc in ("regina_jones", "robert_wilson", "cassius_ryder", "wakako_okada", "dakota_smith"):
        assert facts(client, npc) == set(), npc


def test_preset_3_wraiths_camp_in_the_badlands(client):
    happen(client, "wraiths_camp_badlands", 41)
    assert len(facts(client, "dakota_smith")) == 4
    at(client, 42)
    two = {"A Wraiths raider camp in the Badlands is empty now", "A merc killed the raiders"}
    assert facts(client, "wakako_okada") == two and facts(client, "el_capitan") == two
    at(client, 60)
    for npc in ("regina_jones", "robert_wilson", "cassius_ryder", "dino_dinovic", "padre", "mr_hands"):
        assert facts(client, npc) == set(), npc


def test_kabuki_counts_as_watson(client):
    at(client, 41)
    client.post(
        "/api/events",
        json={
            "type": "x",
            "location": "kabuki",
            "facts": [{"text": "A fight broke out in Kabuki", "importance": 5}],
            "witnesses": [],
        },
    )
    at(client, 42)
    assert facts(client, "regina_jones") == {"A fight broke out in Kabuki"}  # same town
    assert facts(client, "dino_dinovic") == {"A fight broke out in Kabuki"}  # next town
    assert facts(client, "padre") == set()
