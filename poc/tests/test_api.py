"""API tests with a fake LLM and no TTS (no network)."""

import importlib
import json
import re

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


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "1e400"])
def test_clock_advance_with_a_non_number_is_400_and_the_clock_stays(client, raw):
    """Regression: days = NaN passed the range check and set the clock to NaN."""
    r = client.post("/api/clock/advance", content=f'{{"days": {raw}}}', headers={"content-type": "application/json"})
    assert r.status_code == 400
    assert client.get("/api/world").json()["day"] == 41


def test_event_shows_in_the_engine_console(client, caplog, monkeypatch):
    # Each reported event shows in the console with the talk log (TALK_LOG full or short); off hides it.
    import logging

    log = logging.getLogger("dialog")
    log.addHandler(caplog.handler)
    try:
        for mode in ("full", "short"):
            caplog.clear()
            monkeypatch.setenv("TALK_LOG", mode)
            client.post("/api/events", json={"preset": "embershard_cleared"})
            text = caplog.text
            assert "--- event: " in text and ", day 41.00 (" in text and "witnesses: " in text and "(hrolf)" in text
            assert re.search(r"^  \[\d\] \S", text, re.M)
            assert "new memories now: 1" in text
        caplog.clear()
        monkeypatch.setenv("TALK_LOG", "off")
        client.post("/api/events", json={"preset": "embershard_cleared"})
        assert "--- event" not in caplog.text
    finally:
        log.removeHandler(caplog.handler)


def test_event_log_error_does_not_fail_the_event(client, monkeypatch):
    # Code review: the event is stored before the log; a log error must not give 500 (a retry would duplicate it).
    import engine.api as api

    def boom(*a):
        raise RuntimeError("log")

    monkeypatch.setattr(api, "event_log_text", boom)
    assert client.post("/api/events", json={"preset": "embershard_cleared"}).status_code == 200


def test_event_log_keeps_one_fact_on_one_line():
    from engine.dialog import event_log_text
    from engine.models import Fact, WorldEvent

    ev = WorldEvent(
        id="x#1", type="fight", location="town", day=1.0, facts=[Fact(text="a\nb", importance=2)], witnesses=[]
    )
    assert "  [2] a\\nb" in event_log_text(ev, [], 0)
