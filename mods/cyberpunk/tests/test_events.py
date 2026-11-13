"""Game events and the clock (mod spec what/events.md). Offline.

The "who knows what" examples run against the engine API with the Cyberpunk world, with the clock set from game hours
and the events in the form that the mod sends. The mod's own choices (importance, fact text, limits) are checked in
its script, because the game is needed to run it.
"""

import importlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MOD = Path(__file__).resolve().parents[1]
WORLD = json.loads((MOD / "world.json").read_text(encoding="utf-8"))
SCRIPTS = MOD / "r6" / "scripts" / "genpc"
EVENTS = (SCRIPTS / "Events.reds").read_text(encoding="utf-8")
NPC = (SCRIPTS / "Npc.reds").read_text(encoding="utf-8")

NIGHT = 10 * 24 + 22  # game hour 262: day 10 at 22:00
WITNESS_FACT = "The merc was the person who is talking to you now."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("POC_VAR_DIR", str(tmp_path))
    monkeypatch.setenv("POC_DB", str(tmp_path / "test-world.db"))
    monkeypatch.setenv("TTS_ENABLED", "0")
    import engine.api as api

    c = TestClient(importlib.reload(api).app)
    assert c.post("/api/world", json=WORLD).status_code == 200
    return c


def hours(client, h):
    """Rules 1-3: the mod sends the game hours."""
    return client.post("/api/clock/set", json={"hours": h})


def send(client, type_, place, facts, witnesses=()):
    r = client.post(
        "/api/events",
        json={
            "type": type_,
            "location": place,
            "facts": [{"text": t, "importance": i} for t, i in facts],
            "witnesses": list(witnesses),
        },
    )
    assert r.status_code == 200, r.text


def knows(client, npc):
    r = client.get(f"/api/npc/{npc}/knowledge")
    assert r.status_code == 200, r.text
    return {f["text"] for m in r.json()["memories"] for f in m["facts"]}


def crowd_witness(client, entity, town):
    """Rule 21: the mod adds a witness the same way as for a conversation."""
    r = client.post("/api/npcs", json={"entity_id": entity, "name": "Noodle vendor", "settlement": town})
    assert r.status_code == 200, r.text
    return r.json()["npc_id"]


# ---------- "Who knows what" examples ----------
def test_four_maelstrom_members_in_northside_at_night(client):
    assert hours(client, NIGHT).status_code == 200
    vendor = crowd_witness(client, "1234567", "watson")
    kill = "A merc killed 4 Maelstrom members in Northside."
    send(client, "fight", "northside", [(kill, 4), ("It happened at night.", 1), (WITNESS_FACT, 1)], [vendor])
    assert knows(client, vendor) == {kill, "It happened at night.", WITNESS_FACT}
    hours(client, NIGHT + 11.9)
    assert knows(client, "robert_wilson") == set()
    hours(client, NIGHT + 12)
    assert knows(client, "robert_wilson") == {kill} and knows(client, "regina_jones") == {kill}
    assert knows(client, "wakako_okada") == set()
    hours(client, NIGHT + 24)
    assert knows(client, "wakako_okada") == {kill} and knows(client, "dino_dinovic") == {kill}
    hours(client, NIGHT + 24 * 30)
    for npc in ("mr_hands", "padre", "el_capitan", "dakota_smith"):
        assert knows(client, npc) == set(), npc


def test_one_tyger_claws_member_stays_in_westbrook(client):
    hours(client, 100)
    kill = "A merc killed 1 Tyger Claws member in Japantown."
    send(client, "fight", "japantown", [(kill, 3), ("It happened in the morning.", 1)])
    hours(client, 112)
    assert knows(client, "wakako_okada") == {kill}
    hours(client, 100 + 24 * 30)
    for npc in ("robert_wilson", "dino_dinovic", "dakota_smith"):
        assert knows(client, npc) == set(), npc


def test_three_wraiths_in_rocky_ridge(client):
    # Rule 5a: each area of the Badlands is the town "badlands".
    hours(client, 100)
    kill = "A merc killed 3 Wraiths members in the Badlands."
    send(client, "fight", "badlands", [(kill, 4), ("It happened in the afternoon.", 1)])
    hours(client, 112)
    assert knows(client, "dakota_smith") == {kill} and knows(client, "wakako_okada") == set()
    hours(client, 124)
    assert knows(client, "wakako_okada") == {kill} and knows(client, "el_capitan") == {kill}
    assert knows(client, "robert_wilson") == set()


def test_gig_monster_hunt_in_little_china(client):
    hours(client, 200)
    gig = "A merc finished the gig 'Monster Hunt' in Little China."
    send(client, "gig", "little_china", [(gig, 4), ("It happened at night.", 1)])  # rule 13a: no witnesses
    hours(client, 212)
    assert knows(client, "regina_jones") == {gig}
    hours(client, 224)
    assert knows(client, "wakako_okada") == {gig} and knows(client, "dino_dinovic") == {gig}
    hours(client, 200 + 24 * 30)
    assert knows(client, "mr_hands") == set()


def test_ordinary_people_and_police_go_to_the_next_towns(client):
    # Rule 7 (owner question 4): even 1 ordinary person or police officer is importance 4.
    hours(client, 300)
    kill = "A merc killed 1 ordinary person in Kabuki."
    send(client, "fight", "kabuki", [(kill, 4)])
    hours(client, 324)
    assert knows(client, "dino_dinovic") == {kill}


def test_police_chase(client):
    hours(client, 400)
    chase = "The NCPD chased a merc through Kabuki."
    send(client, "police_chase", "kabuki", [(chase, 3), ("The merc got away.", 2)])
    hours(client, 412)
    assert knows(client, "regina_jones") == {chase}
    hours(client, 400 + 24 * 30)
    assert knows(client, "wakako_okada") == set()


def test_older_save_the_clock_stays(client):
    # Rule 4: the engine refuses earlier game hours. The clock stays.
    assert hours(client, 720).status_code == 200
    r = hours(client, 240)
    assert r.status_code == 400 and r.json()["detail"]["day"] == pytest.approx(30)
    assert hours(client, 744).status_code == 200


def test_dogtown_reaches_only_witnesses(client):
    # Rule 5c.
    hours(client, 100)
    vendor = crowd_witness(client, "7654321", "pacifica")
    send(client, "fight", "dogtown", [("A merc killed 5 Barghest members in Dogtown.", 4)], [vendor])
    hours(client, 100 + 24 * 30)
    assert knows(client, "mr_hands") == set() and knows(client, vendor)


# ---------- The mod's script ----------
def test_place_ids_cover_the_world_file():
    # Rules 5, 5a: every place and town of the world file, and the Badlands areas.
    ids = set(re.findall(r'case gamedataDistrict\.\w+: return "(\w+)";', NPC))
    world = {p["id"] for p in WORLD["locations"]} | {t["id"] for t in WORLD["settlements"]}
    assert ids == world
    for area in ("NorthBadlands", "SouthBadlands", "MorroRock"):
        assert f'case gamedataDistrict.{area}: return "badlands";' in NPC
    names = dict(re.findall(r'case "(\w+)": return "([^"]+)";', NPC[NPC.index("func PlaceName") :]))
    assert world | {"dogtown"} <= set(names)
    assert names["badlands"] == "the Badlands" and names["northside"] == "Northside"


def test_fight_rules_in_script():
    assert "this.playSeconds - this.lastKill < 60" in EVENTS and "player.IsInCombat()" in EVENTS  # rule 6a
    assert 'e.type = "fight";' in EVENTS and 'e.type = "gig";' in EVENTS and 'e.type = "police_chase";' in EVENTS
    # Rule 7: police and ordinary people 4 or 5; factions 3, 4 or 5.
    imp = EVENTS[EVENTS.index("func Importance") :]
    assert "if kind == 1 || kind == 2 {\n      return n <= 2 ? 4 : 5;" in imp
    assert "if n <= 2 {\n      return 3;\n    }\n    return n <= 9 ? 4 : 5;" in imp
    assert '"killed or knocked out"' in EVENTS and '"knocked out"' in EVENTS  # rule 7a
    for t in ("in the morning", "in the afternoon", "in the evening", "at night"):
        assert f'"It happened {t}."' in EVENTS  # rule 7b
    assert (
        "hour >= 6 && hour < 12" in EVENTS
        and "hour >= 12 && hour < 18" in EVENTS
        and "hour >= 18 && hour < 22" in EVENTS
    )
    assert '"unknown people"' in EVENTS and '"ordinary person"' in EVENTS  # rule 7c, singular forms
    assert "GenpcNpc.IsStoryCharacter(GenpcNpc.Name(npc))" in EVENTS  # rule 9


def test_witness_rules_in_script():
    assert "query.maxDistance = 20.0;" in EVENTS and "Distance(npc, player) <= 20.0" in EVENTS  # witness range
    assert "while ArraySize(list) > 5" in EVENTS  # rule 20
    assert f'"{WITNESS_FACT}"' in EVENTS and '!Equals(e.type, "gig")' in EVENTS  # rules 21b, 13a
    assert "left out" in EVENTS  # rule 21a


def test_chase_gig_and_drop_rules_in_script():
    assert "this.chaseStars >= 2" in EVENTS and "this.chaseStars >= 4 ? 4 : 3" in EVENTS  # rules 14, 15
    gig = EVENTS[EVENTS.index("func IsGig") :]
    assert "Contract" in gig and "SideQuest" in gig and "MinorQuest" in gig and "MainQuest" not in gig  # rule 11
    assert "gameJournalEntryState.Succeeded" in EVENTS
    assert 'this.Drop("load");' in EVENTS and 'events.Drop("player died");' in EVENTS  # rules 6c, 14a
    assert 'this.Drop("setting off");' in EVENTS  # rule 6d
    assert "DelayCallback(cb, 10.0, false);  // rule 23" in EVENTS


def test_clock_rules_in_script():
    assert "GetGameTimeStamp() / 3600.0" in EVENTS  # game hours
    assert "this.playSeconds % 60 == 0" in EVENTS  # rule 2
    system = (SCRIPTS / "System.reds").read_text(encoding="utf-8")
    assert 'this.SendClock("load");  // events.md rule 1' in system
    assert 'this.SendClock("greeting");  // events.md rule 2' in system
    assert '"/api/clock/set", this.ClockBody(), n"OnEventClock"' in EVENTS  # before each event


def test_send_events_setting():
    settings = (SCRIPTS / "Settings.reds").read_text(encoding="utf-8")
    assert '"Send game events")' in settings and "public let eventsOn: Bool = true;" in settings  # rule 24
