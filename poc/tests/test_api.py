"""API tests with a fake LLM and no TTS (no network)."""

import importlib
import json

import pytest
from fastapi.testclient import TestClient

from engine.providers.llm import LLMResult


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


def test_full_flow(client):
    w = client.get("/api/world").json()
    assert w["day"] == 41 and {n["id"] for n in w["npcs"]} >= {"hrolf", "torvald", "eirik", "sabine"}
    r = client.post("/api/events", json={"preset": "embershard_cleared"}).json()
    assert [m["npc_id"] for m in r["new_memories"]] == ["hrolf"]
    slot = client.post("/api/saves", json={"label": "after mine"}).json()["id"]
    assert client.post("/api/clock/advance", json={"days": 3}).json()["day"] == 44

    k = client.get("/api/npc/eirik/knowledge").json()
    (m,) = k["memories"]
    assert m["source"] == "hop2" and {f["importance"] for f in m["kept"]} == {4, 5}
    assert {f["importance"] for f in m["lost_in_retelling"]} == {1, 2, 3}

    t = client.post("/api/dialog/open", json={"npc_id": "eirik"}).json()
    assert t["npc_line"] == "Well met." and len(t["choices"]) == 3
    t2 = client.post("/api/dialog/choose", json={"npc_id": "eirik", "session_id": t["session_id"], "text": "hi"}).json()
    assert t2["session_id"] == t["session_id"]
    assert t2["sent"]["messages"][-1] == {"role": "user", "content": "hi"}
    assert "Eirik" in t2["sent"]["system"] and t2["raw_reply"]

    assert "Embershard" not in client.get("/api/npc/sabine/prompt").json()["prompt"]
    client.post(f"/api/saves/{slot}/load")
    assert client.get("/api/npc/eirik/knowledge").json()["memories"] == []
    assert client.post("/api/reset").json()["day"] == 41
    assert client.get("/api/world").json()["events"] == []


def test_validation(client):
    assert client.post("/api/clock/advance", json={"days": -1}).status_code == 400
    assert client.post("/api/dialog/open", json={"npc_id": "nobody"}).status_code == 404
    assert client.post("/api/events", json={"preset": "nope"}).status_code == 404
    assert client.get("/api/audio/1").status_code == 404  # TTS disabled


def test_clock_set_moves_forward_only(client):
    client.post("/api/events", json={"preset": "embershard_cleared"})
    r = client.post("/api/clock/set", json={"day": 41.6}).json()  # past the 0.5-day first gossip hop
    assert r["day"] == 41.6 and r["new_memories"]
    same = client.post("/api/clock/set", json={"day": 41.6})
    assert same.status_code == 200 and same.json() == {"day": 41.6, "new_memories": []}
    back = client.post("/api/clock/set", json={"day": 41.0})
    assert back.status_code == 409 and "load a save" in back.json()["detail"]
    assert client.get("/api/world").json()["day"] == 41.6  # a rejected set leaves the clock alone
    raw = {"content-type": "application/json"}
    for bad in ('{"day": NaN}', '{"day": 1e999}'):  # 1e999 parses as inf
        assert client.post("/api/clock/set", content=bad, headers=raw).status_code == 400
    assert client.post("/api/clock/set", json={"day": 41.6 + 366}).status_code == 400  # runaway jump
    assert client.get("/api/world").json()["day"] == 41.6


def test_set_day_stores_the_exact_time(tmp_path):
    # regression: storing old + (new - old) gave 0.9300000000000002, so re-sending 0.93 got a 409
    from pathlib import Path

    from engine.store import Store, load_world

    world = load_world(Path(__file__).resolve().parents[1] / "data" / "world.json")
    s = Store(tmp_path / "s.db", world, start_day=0.34)
    s.set_day(0.93)
    assert s.day == 0.93
    with pytest.raises(ValueError):
        s.set_day(0.5)


def test_clock_set_repeated_sync_is_not_backwards(client):
    for day in (41.34, 41.93, 41.93, 41.93 - 1e-9):  # last one: jitter below CLOCK_EPS
        r = client.post("/api/clock/set", json={"day": day})
        assert r.status_code == 200, (day, r.json())
    assert client.get("/api/world").json()["day"] == 41.93


def test_clock_set_equal_time_adds_no_gossip(client):
    client.post("/api/events", json={"preset": "embershard_cleared"})  # first hop is due at 41.5
    assert client.post("/api/clock/set", json={"day": 41.0}).json()["new_memories"] == []
