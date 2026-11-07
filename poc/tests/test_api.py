"""API tests with a fake LLM and no TTS (no network)."""
import importlib
import json

import pytest
from fastapi.testclient import TestClient

from engine.providers.llm import LLMResult


class FakeLLM:
    name = "fake"

    def complete_json(self, system, messages):
        return LLMResult(text=json.dumps({"npc_line": "Well met.", "choices": ["a", "b", "Goodbye."],
                                          "remember": []}), ms=1.0)


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
