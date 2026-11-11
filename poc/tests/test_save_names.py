"""Saves by a name that the mod gives (spec #11).

Rules: saves-and-clock.md 12a-12f, 15a-15e, 17; http-api.md 23a-23d, 24a-24c.
Offline: a fake LLM and no TTS.
"""

import importlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from engine.providers.llm import LLMResult
from engine.store import Store, load_world


class FakeLLM:
    name = "fake"

    def complete_json(self, system, messages):
        return LLMResult(
            text=json.dumps({"npc_line": "Well met.", "choices": ["a", "b", "Goodbye."], "remember": []}), ms=1.0
        )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("POC_VAR_DIR", str(tmp_path))
    monkeypatch.setenv("POC_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("TTS_ENABLED", "0")
    import engine.api as api

    api = importlib.reload(api)
    api._llm = FakeLLM()
    return TestClient(api.app)


def _save(client, **body):
    return client.post("/api/saves", json=body)


def _load(client, ref):
    return client.post(f"/api/saves/{ref}/load")


def _saves(client):
    return client.get("/api/world").json()["saves"]


def test_same_name_replaces_the_save(client):
    """Example: save as quick-0 on day 41 and again on day 42. A load of quick-0 gives day 42 (rules 12d, 12e, 23b)."""
    first = _save(client, token="quick-0", label="first").json()["id"]
    client.post("/api/clock/advance", json={"days": 1})
    r = _save(client, token="quick-0", label="second").json()
    assert r["id"] == first  # the old save number
    (s,) = [s for s in r["saves"] if s["token"] == "quick-0"]
    assert (s["id"], s["label"], s["day"]) == (first, "second", 42)
    client.post("/api/clock/advance", json={"days": 3})
    assert _load(client, "quick-0").json() == {"day": 42}


def test_save_without_name_is_always_new(client):
    """Rules 12f, 23d: a save without a save name never replaces a save; its token is null."""
    a = _save(client, label="x").json()["id"]
    b = _save(client, label="x").json()["id"]
    named = _save(client, token="cp-1").json()["id"]
    assert len({a, b, named}) == 3
    assert [s["token"] for s in _saves(client)] == [None, None, "cp-1"]


@pytest.mark.parametrize(
    "token",
    ["", "1042", "a" * 65, "cp*1042", "cp 1042", "café", "cp/1", "cp\n1", "---", 5, ["cp-1"], True],
)
def test_bad_save_name_makes_no_save(client, token):
    """Rules 12b, 12c, 23c: a bad save name is 400, and the engine makes no save."""
    r = _save(client, token=token)
    assert r.status_code == 400
    assert _saves(client) == []


@pytest.mark.parametrize("token", ["a", "Z" * 64, "cp-1042", "quick_0.v2", "1a"])
def test_good_save_names(client, token):
    """Rule 12b-12c: 1 to 64 characters from the list, with one letter or more."""
    assert _save(client, token=token).status_code == 200
    assert _load(client, token).status_code == 200


def test_load_by_name_removes_later_knowledge(client):
    """Rules 15a, 14: a load by save name works like a load by save number."""
    _save(client, token="cp-1")
    client.post("/api/events", json={"preset": "embershard_cleared"})
    assert client.get("/api/npc/hrolf/knowledge").json()["memories"]
    assert _load(client, "cp-1").json() == {"day": 41}
    assert client.get("/api/npc/hrolf/knowledge").json()["memories"] == []


def test_unknown_name_changes_nothing(client):
    """Example and rule 15b: no save has the name cp-0007. The engine answers 404 and changes nothing."""
    _save(client, token="cp-1")
    client.post("/api/events", json={"preset": "embershard_cleared"})
    client.post("/api/clock/advance", json={"days": 2})
    before = client.get("/api/npc/hrolf/knowledge").json()
    assert _load(client, "cp-0007").status_code == 404
    assert client.get("/api/world").json()["day"] == 43
    assert client.get("/api/npc/hrolf/knowledge").json() == before


def test_digits_load_a_save_number(client):
    """Rule 24b: a value with only digits is a save number."""
    first = _save(client, label="by number").json()["id"]
    client.post("/api/clock/advance", json={"days": 1})
    assert _load(client, str(first)).json() == {"day": 41}
    assert _load(client, "999").status_code == 404
    assert _load(client, "9" * 30).status_code == 404  # too big for a save number: no save, not a crash


@pytest.mark.parametrize("ref", ["cp*1042", "a" * 65, "caf%C3%A9", "cp%201042"])
def test_bad_name_in_load_is_400(client, ref):
    """Rule 24c: a value that breaks rule 12b is 400."""
    _save(client, token="cp-1042")
    assert _load(client, ref).status_code == 400


def test_load_by_name_and_added_npcs(client):
    """Rule 15e: after a load by save name, no crowd NPC exists, and an added named NPC stays (rules 13a-13b)."""
    named = {"record_id": "npc.ferry_hand", "name": "Ola", "settlement": "riverwood"}
    crowd = {"entity_id": "1874320956", "name": "Dock worker", "settlement": "riverwood"}
    assert client.post("/api/npcs", json=named).status_code == 200
    _save(client, token="cp-1")
    assert client.post("/api/npcs", json=crowd).status_code == 200
    _load(client, "cp-1")
    ids = {n["id"] for n in client.get("/api/world").json()["npcs"]}
    assert "npc.ferry_hand" in ids and "crowd-1874320956" not in ids


def test_reset_keeps_named_saves(client):
    """Rules 15c, 17: the engine does not remove saves; a reset keeps them."""
    _save(client, token="cp-1")
    client.post("/api/reset")
    assert [s["token"] for s in _saves(client)] == ["cp-1"]
    assert _load(client, "cp-1").status_code == 200


def test_database_from_before_save_names(tmp_path):
    """A database made before save names gets the token column. Its old saves have no save name."""
    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE saves (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT, day REAL, created REAL, blob TEXT NOT NULL)"
    )
    blob = {"meta": [{"k": "day", "v": "41.0"}], "events": [], "memories": [], "turns": []}
    db.execute("INSERT INTO saves(label, day, created, blob) VALUES('old', 41, 0, ?)", (json.dumps(blob),))
    db.commit()
    db.close()
    world = load_world("poc/data/world.json")
    store = Store(path, world, start_day=41)
    assert [(s["label"], s["token"]) for s in store.saves()] == [("old", None)]
    assert store.save("new", "cp-1") == 2 and store.save_id("cp-1") == 2
    store.load(1)
    assert store.day == 41
