"""A mod sends its own world (spec #7: world-file.md rules 15-16s, http-api.md rules 6a, 8a-8d, 12a).

Offline: a fake LLM and no TTS. `harbor_city` is a made-up mod world.
"""

import copy
import importlib
import json

import pytest
from fastapi.testclient import TestClient

from engine.providers.llm import LLMResult

HARBOR = {
    "id": "harbor_city",
    "start_day": 0,
    "setting": "Talk like a sailor from a harbor town.",
    "settlements": [
        {"id": "docks", "name": "The Docks", "adjacent": ["market"]},
        {"id": "market", "name": "The Market", "adjacent": ["docks"]},
    ],
    "npcs": [
        {"id": "dockworker_1", "name": "Mara", "role": "dockworker", "settlement": "docks", "bio": "Loads ships."},
        {"id": "bram", "name": "Bram", "role": "fishmonger", "settlement": "market", "bio": "Sells fish."},
    ],
}

GULL = {
    "id": "gull_island",
    "start_day": 5,
    "settlements": [{"id": "village", "name": "Gull Village"}],
    # same NPC id as in the test world, on purpose (leak test)
    "npcs": [{"id": "torvald", "name": "Torvald", "role": "fisher", "settlement": "village", "bio": "Mends nets."}],
}

STORM = {"text": "A storm sank a ship at the docks", "importance": 5}


class FakeLLM:
    name = "fake"

    def complete_json(self, system, messages):
        return LLMResult(
            text=json.dumps({"npc_line": "Aye.", "choices": ["a", "b", "Goodbye."], "remember": []}), ms=1.0
        )


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("POC_VAR_DIR", str(tmp_path))
    monkeypatch.setenv("POC_DB", str(tmp_path / "test-world.db"))
    monkeypatch.setenv("TTS_ENABLED", "0")
    import engine.api as api

    api = importlib.reload(api)  # a reload is an engine restart
    api._llm = FakeLLM()
    return api, TestClient(api.app)


@pytest.fixture
def client(tmp_path, monkeypatch):
    return make_client(tmp_path, monkeypatch)[1]


def send(client, world):
    return client.post("/api/world", json=world)


def storm(client, witnesses):
    return client.post(
        "/api/events", json={"type": "storm", "location": "docks", "facts": [STORM], "witnesses": witnesses}
    )


# ---------- Summary example 1: switch to a mod world ----------
def test_mod_world_replaces_test_world_and_starts_at_its_start_day(client):
    assert client.post("/api/session/start").json()["world"] == "test"
    r = send(client, HARBOR)
    assert r.status_code == 200
    assert r.json() == {"world": "harbor_city", "towns": 2, "npcs": 2}
    w = client.get("/api/world").json()
    assert w["world"] == "harbor_city" and w["day"] == 0
    assert {n["id"] for n in w["npcs"]} == {"dockworker_1", "bram"}
    assert client.post("/api/dialog/open", json={"npc_id": "torvald"}).status_code == 404
    assert client.post("/api/session/start").json()["world"] == "harbor_city"


# ---------- Summary examples 2 and 3: knowledge survives a restart and a switch ----------
def test_world_keeps_its_clock_and_memories_across_restart(tmp_path, monkeypatch):
    _, c = make_client(tmp_path, monkeypatch)
    send(c, HARBOR)
    assert storm(c, ["dockworker_1"]).status_code == 200
    c.post("/api/clock/advance", json={"days": 12})

    _, c = make_client(tmp_path, monkeypatch)  # engine restart
    assert c.post("/api/session/start").json()["world"] == "test"  # rule 16q
    assert c.get("/api/world").json()["day"] == 41  # the test world's own clock
    send(c, HARBOR)
    assert c.get("/api/world").json()["day"] == 12
    mems = c.get("/api/npc/dockworker_1/knowledge").json()["memories"]
    assert [f["text"] for m in mems for f in m["facts"]] == [STORM["text"]]


def test_switch_between_two_mod_worlds_keeps_each_clock(client):
    send(client, HARBOR)
    client.post("/api/clock/advance", json={"days": 3})
    send(client, GULL)
    assert client.get("/api/world").json()["day"] == 5
    send(client, HARBOR)
    assert client.get("/api/world").json()["day"] == 3


# ---------- Summary example 4 and rules 16m-16n, 8c-8d: a wrong world ----------
@pytest.mark.parametrize(
    "change, reason",
    [
        (lambda w: w["npcs"][0].update(settlement="nowhere"), "unknown town 'nowhere'"),
        (lambda w: w["settlements"][0].update(adjacent=["nowhere"]), "unknown next town 'nowhere'"),
        (lambda w: w["npcs"].append(dict(w["npcs"][0])), "two npcs have the id 'dockworker_1'"),
        (lambda w: w.update(locations=[{"id": "pier", "name": "Pier", "near_settlement": "x"}]), "unknown town 'x'"),
        (lambda w: w.pop("id"), "id"),
        (lambda w: w.pop("settlements"), "settlements"),
        (lambda w: w.update(npcs=[]), "no npcs"),
        (lambda w: w.update(id="test"), "cannot use the world name 'test'"),
    ],
)
def test_wrong_world_is_refused_with_400_and_a_reason(client, change, reason):
    bad = copy.deepcopy(HARBOR)
    change(bad)
    r = send(client, bad)
    assert r.status_code == 400  # not 422, also for a missing part
    assert reason in r.json()["detail"]
    assert client.get("/api/world").json()["world"] == "test"  # the world in use stays


def test_body_that_is_not_an_object_is_400(client):
    assert client.post("/api/world", json=[1, 2]).status_code == 400


# ---------- Summary example 5 and rules 16j-16k: a changed world ----------
def test_changed_world_keeps_memories_and_removed_npc_is_unknown(client):
    send(client, HARBOR)
    storm(client, ["dockworker_1"])
    without = copy.deepcopy(HARBOR)
    without["npcs"] = [n for n in without["npcs"] if n["id"] != "dockworker_1"]
    send(client, without)
    assert client.post("/api/dialog/open", json={"npc_id": "dockworker_1"}).status_code == 404
    send(client, HARBOR)  # a later update adds the NPC again
    mems = client.get("/api/npc/dockworker_1/knowledge").json()["memories"]
    assert len(mems) == 1


def test_changed_next_towns_apply_to_gossip_that_has_not_arrived(client):
    send(client, HARBOR)
    storm(client, ["dockworker_1"])
    lonely = copy.deepcopy(HARBOR)
    lonely["settlements"] = [{"id": "docks", "name": "The Docks"}, {"id": "market", "name": "The Market"}]
    send(client, lonely)
    client.post("/api/clock/advance", json={"days": 5})
    assert client.get("/api/npc/bram/knowledge").json()["memories"] == []


# ---------- rules 16f and REVIEW §1: nothing crosses between worlds ----------
def test_same_npc_id_in_two_worlds_sees_only_its_own_world(client):
    r = client.post("/api/events", json={"preset": "embershard_cleared", "witnesses": ["torvald"]})
    assert r.status_code == 200
    test_prompt = client.get("/api/npc/torvald/prompt").json()["prompt"]
    assert "Embershard" in test_prompt
    send(client, GULL)
    prompt = client.get("/api/npc/torvald/prompt").json()["prompt"]
    assert "Embershard" not in prompt and "bandit" not in prompt.lower()
    assert "Gull Village" in prompt
    assert client.get("/api/npc/torvald/knowledge").json()["memories"] == []
    assert client.get("/api/world").json()["events"] == []


def test_saves_reset_and_load_belong_to_the_world_in_use(client):
    send(client, HARBOR)
    save_id = client.post("/api/saves", json={"label": "harbor"}).json()["id"]
    storm(client, ["dockworker_1"])
    send(client, GULL)
    assert client.get("/api/world").json()["saves"] == []
    client.post("/api/clock/advance", json={"days": 2})
    assert client.post("/api/reset").json()["day"] == 5  # the gull_island start day
    send(client, HARBOR)
    assert len(client.get("/api/world").json()["events"]) == 1  # the reset did not touch harbor_city
    client.post(f"/api/saves/{save_id}/load")
    assert client.get("/api/world").json()["events"] == []


# ---------- rules 16s and 12a: presets only in the test world ----------
def test_presets_only_in_the_test_world(client):
    assert client.get("/api/world").json()["presets"]
    send(client, HARBOR)
    assert client.get("/api/world").json()["presets"] == {}
    r = client.post("/api/events", json={"preset": "embershard_cleared"})
    assert r.status_code == 404
