"""The Cyberpunk world (mod spec what/world.md). Offline: the engine API with no LLM and no TTS.

The mod talks to the engine only through the HTTP API (decision 0007). The tests start the engine in the same
process and send the world and the presets the way the mod will (engine http-api.md rules 8a and 13).
"""

import copy
import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MOD = Path(__file__).resolve().parents[1]
WORLD = json.loads((MOD / "world.json").read_text(encoding="utf-8"))
PRESETS = json.loads((MOD / "events.json").read_text(encoding="utf-8"))

# The approved tables of the mod spec (rules 3, 5, 6, 9 and 15). A wrong edit of world.json fails here.
NEXT_TOWNS = {
    "watson": {"city_center", "westbrook"},
    "westbrook": {"watson", "city_center", "badlands"},
    "city_center": {"watson", "westbrook", "heywood", "santo_domingo"},
    "heywood": {"city_center", "santo_domingo", "pacifica"},
    "santo_domingo": {"city_center", "heywood", "pacifica", "badlands"},
    "pacifica": {"heywood", "santo_domingo"},
    "badlands": {"westbrook", "santo_domingo"},
}
# The voices of mod spec what/world.md rule 8c. All are premade voices of the voice service (rule 8a).
VOICES = {
    "regina_jones": "EXAVITQu4vr4xnSDxMaL",
    "robert_wilson": "pqHfZKP75CvOlQylNhV4",
    "cassius_ryder": "N2lVS1w4EtoT3dr4eOWO",
    "wakako_okada": "pFZP5JQG7iQjIQuC4Bku",
    "dino_dinovic": "cjVigY5qzO86Huf0OWal",
    "padre": "nPczCjzI2devNBz1zQrb",
    "el_capitan": "IKne3meq5aSn9XLyUdCD",
    "mr_hands": "JBFqnCBsd6RMkjVDRZzb",
    "dakota_smith": "XrExE9yKIg1WjnnlVkGX",
}
VOICE_POOL = {
    "female": ["hpp4J3VqNfWAUOO0d1Us", "FGY2WhTYpPnrIDTdsKH5", "cgSgspJ2msm6clMCkdW9"],
    "male": ["CwhRBWXzGAHq8TQ4Fs17", "iP95p4xoKVk53GoZ742B", "bIHbv24MWmeRgasZH58o"],
}
PLACES = {
    "little_china": "watson",
    "kabuki": "watson",
    "northside": "watson",
    "arasaka_waterfront": "watson",
    "japantown": "westbrook",
    "charter_hill": "westbrook",
    "north_oak": "westbrook",
    "corpo_plaza": "city_center",
    "downtown": "city_center",
    "the_glen": "heywood",
    "wellsprings": "heywood",
    "vista_del_rey": "heywood",
    "arroyo": "santo_domingo",
    "rancho_coronado": "santo_domingo",
    "coastview": "pacifica",
    "west_wind_estate": "pacifica",
}
CAST = {  # id: (name, role, town)
    "regina_jones": ("Regina Jones", "fixer", "watson"),
    "robert_wilson": ("Robert Wilson", "gun shop owner", "watson"),
    "cassius_ryder": ("Cassius Ryder", "ripperdoc (cyberware doctor)", "watson"),
    "wakako_okada": ("Wakako Okada", "fixer", "westbrook"),
    "dino_dinovic": ("Dino Dinovic", "fixer", "city_center"),
    "padre": ('Sebastian "Padre" Ibarra', "fixer", "heywood"),
    "el_capitan": ('Muamar "El Capitan" Reyes', "fixer", "santo_domingo"),
    "mr_hands": ("Mr. Hands", "fixer", "pacifica"),
    "dakota_smith": ("Dakota Smith", "fixer", "badlands"),
}
SETTING = (
    "Speak like a person who lives in Night City in the year 2077. Night City is a hard, dangerous city. "
    "Corporations and gangs control it. Use some street words, but keep your meaning clear."
)
GENERIC_BIO = "You are an ordinary person in Night City. You have no special story."


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


def at(client, day):
    """Move the clock forward to `day`."""
    now = client.get("/api/world").json()["day"]
    if day > now:
        r = client.post("/api/clock/advance", json={"days": day - now})
        assert r.status_code == 200, r.text
    assert client.get("/api/world").json()["day"] == pytest.approx(max(day, now))


def happen(client, preset, day):
    """Move the clock to `day`, then send the preset in the full form."""
    at(client, day)
    p = PRESETS[preset]
    r = client.post(
        "/api/events",
        json={"type": p["type"], "location": p["location"], "facts": p["facts"], "witnesses": p["default_witnesses"]},
    )
    assert r.status_code == 200, r.text


def facts(client, npc):
    r = client.get(f"/api/npc/{npc}/knowledge")
    assert r.status_code == 200, r.text
    return {f["text"] for m in r.json()["memories"] for f in m["facts"]}


def all_facts(preset):
    return {f["text"] for f in PRESETS[preset]["facts"]}


# ---------- rules 2-15: the world file has the approved content ----------
def test_world_file_matches_the_approved_tables():
    assert WORLD["id"] == "cyberpunk" and WORLD["start_day"] == 0
    assert WORLD["setting"] == SETTING
    assert WORLD["generic_bio"] == GENERIC_BIO
    assert WORLD["rules"] == {"hop2_delay_days": 1.0}
    assert {t["id"]: set(t["adjacent"]) for t in WORLD["settlements"]} == NEXT_TOWNS
    assert {p["id"]: p["near_settlement"] for p in WORLD["locations"]} == PLACES
    assert {n["id"]: (n["name"], n["role"], n["settlement"]) for n in WORLD["npcs"]} == CAST
    assert {n["id"]: n["voice_id"] for n in WORLD["npcs"]} == VOICES
    assert all(n["bio"] for n in WORLD["npcs"])
    assert WORLD["voice_pool"] == VOICE_POOL
    assert "dogtown" not in NEXT_TOWNS


def test_the_engine_accepts_the_world_and_starts_at_day_0(client):
    w = client.get("/api/world").json()
    assert w["world"] == "cyberpunk" and w["day"] == 0
    assert len(w["settlements"]) == 7 and len(w["npcs"]) == 9


def test_only_the_next_town_delay_differs_from_the_defaults(client):
    ours = client.get("/api/world").json()["rules"]
    plain = copy.deepcopy(WORLD)
    plain["id"] = "cyberpunk_default_rules"
    plain.pop("rules")
    assert client.post("/api/world", json=plain).status_code == 200
    defaults = client.get("/api/world").json()["rules"]
    assert ours["hop2_delay_days"] == 1.0 and defaults["hop2_delay_days"] != 1.0
    assert {k: v for k, v in ours.items() if k != "hop2_delay_days"} == {
        k: v for k, v in defaults.items() if k != "hop2_delay_days"
    }


# ---------- Summary examples 1-4 and the preset 1 examples ----------
def test_preset_1_gig_in_northside(client):
    happen(client, "maelstrom_gig_northside", 41)
    assert facts(client, "regina_jones") == all_facts("maelstrom_gig_northside")
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
    for npc in CAST:
        if npc != "mr_hands":
            assert facts(client, npc) == set(), npc


# ---------- preset 2 and preset 3 examples ----------
def test_preset_2_police_fight_in_the_glen(client):
    happen(client, "police_fight_the_glen", 41)
    assert facts(client, "padre") == all_facts("police_fight_the_glen")
    at(client, 42)
    two = {"A merc fought the police in The Glen", "Two police officers died"}
    for npc in ("dino_dinovic", "el_capitan", "mr_hands"):
        assert facts(client, npc) == two, npc
    at(client, 60)
    for npc in ("regina_jones", "robert_wilson", "cassius_ryder", "wakako_okada", "dakota_smith"):
        assert facts(client, npc) == set(), npc


def test_preset_3_wraiths_camp_in_the_badlands(client):
    happen(client, "wraiths_camp_badlands", 41)
    assert facts(client, "dakota_smith") == all_facts("wraiths_camp_badlands")
    at(client, 42)
    two = {"A Wraiths raider camp in the Badlands is empty now", "A merc killed the raiders"}
    assert facts(client, "wakako_okada") == two and facts(client, "el_capitan") == two
    at(client, 60)
    for npc in ("regina_jones", "robert_wilson", "cassius_ryder", "dino_dinovic", "padre", "mr_hands"):
        assert facts(client, npc) == set(), npc


# ---------- rule 5 example: Kabuki counts as Watson ----------
def test_kabuki_counts_as_watson(client):
    at(client, 41)
    r = client.post(
        "/api/events",
        json={
            "type": "x",
            "location": "kabuki",
            "facts": [{"text": "A fight broke out in Kabuki", "importance": 5}],
            "witnesses": [],
        },
    )
    assert r.status_code == 200
    at(client, 42)
    news = {"A fight broke out in Kabuki"}
    assert facts(client, "regina_jones") == news  # same town
    assert facts(client, "dino_dinovic") == news and facts(client, "wakako_okada") == news  # next towns
    assert facts(client, "padre") == set()
