"""The voice goes into slot files that a game mod plays (spec #10).

Rules: http-api.md 29, 30a-30n, session start `audio_slots`; system-overview.md settings
`AUDIO_SLOT_DIR` and `AUDIO_SLOT_COUNT`. Offline: a fake LLM and a fake voice service.
"""

import importlib
import json
import threading

import pytest
from fastapi.testclient import TestClient

from engine.providers.llm import LLMResult


class FakeLLM:
    name = "fake"

    def complete_json(self, system, messages):
        return LLMResult(
            text=json.dumps({"npc_line": "Well met.", "choices": ["a", "b", "Goodbye."], "remember": []}), ms=1.0
        )


class FakeTTS:
    """Sends the sound in parts, like the real voice service. `fail` makes the next calls fail."""

    name = "fake-tts"
    media_type = "audio/mpeg"

    def __init__(self):
        self.calls = 0
        self.fail = False
        self.gate = None  # a threading.Barrier: hold calls until all arrive

    def stream(self, text, voice_id):
        self.calls += 1
        if self.gate:
            self.gate.wait(timeout=5)
        if self.fail:
            raise RuntimeError("ElevenLabs 500: down")
        yield b"part1-"
        yield f"{text}|{voice_id}|{self.calls}".encode()


def _load(tmp_path, monkeypatch, slot_dir="slots", count="4", make_dir=True):
    """Reload the engine with these settings only. The developer's `.env` is not read."""
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("POC_VAR_DIR", str(tmp_path))
    monkeypatch.setenv("POC_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("TTS_ENABLED", "0")
    if slot_dir is None:
        monkeypatch.setenv("AUDIO_SLOT_DIR", "")
    else:
        folder = tmp_path / slot_dir
        if make_dir:
            folder.mkdir(exist_ok=True)
        monkeypatch.setenv("AUDIO_SLOT_DIR", str(folder))
    monkeypatch.setenv("AUDIO_SLOT_COUNT", count)
    import engine.api as api

    return importlib.reload(api)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """The engine with the voice on, 4 slot files (the default) and a slot folder."""
    api = _load(tmp_path, monkeypatch)
    api._llm = FakeLLM()
    api.tts = FakeTTS()
    return api, TestClient(api.app), tmp_path / "slots"


def _turns(client, n, npc="eirik"):
    """Make n turns with one NPC. Returns their turn numbers."""
    t = client.post("/api/dialog/open", json={"npc_id": npc}).json()
    ids = [t["turn_id"]]
    while len(ids) < n:
        t = client.post("/api/dialog/choose", json={"npc_id": npc, "session_id": t["session_id"], "text": "hi"}).json()
        ids.append(t["turn_id"])
    return ids


def _slot(client, turn_id):
    return client.post(f"/api/audio/{turn_id}/slot")


def test_slot_answer_and_full_file(env):
    """Rules 30a, 30c, 30f, 30g: the first request gets slot 1; the file has the full voice."""
    api, client, folder = env
    (tid,) = _turns(client, 1)
    r = _slot(client, tid)
    assert r.status_code == 200
    body = r.json()
    assert body == {"turn_id": tid, "slot": "genpc_voice_1", "file": str((folder / "genpc_voice_1.mp3").resolve())}
    assert (folder / "genpc_voice_1.mp3").read_bytes() == b"part1-Well met.|SOYHLrjzK2X1ezoPC6cr|1"
    assert [p.name for p in folder.iterdir()] == ["genpc_voice_1.mp3"]  # no temp file is left


def test_rotation_wraps_after_last_slot(env):
    """Rule 30d and the example: with 4 slot files, the fifth voice goes into genpc_voice_1.mp3."""
    api, client, folder = env
    ids = _turns(client, 5)
    slots = [_slot(client, t).json()["slot"] for t in ids]
    assert slots == ["genpc_voice_1", "genpc_voice_2", "genpc_voice_3", "genpc_voice_4", "genpc_voice_1"]
    assert sorted(p.name for p in folder.iterdir()) == [f"genpc_voice_{n}.mp3" for n in (1, 2, 3, 4)]
    assert (folder / "genpc_voice_1.mp3").read_bytes().endswith(b"|5")  # the fifth voice


def test_same_turn_again_is_a_new_request(env):
    """Rule 30d: a second request for the same turn makes the voice again and uses the next slot file."""
    api, client, folder = env
    (tid,) = _turns(client, 1)
    assert _slot(client, tid).json()["slot"] == "genpc_voice_1"
    assert _slot(client, tid).json()["slot"] == "genpc_voice_2"
    assert api.tts.calls == 2


def test_failed_voice_keeps_old_sound_and_uses_its_slot(env):
    """Rules 30j, 30k and the example: turns 12, 13 use slots 1, 2; turn 14 fails on slot 3; then slot 4."""
    api, client, folder = env
    old = folder / "genpc_voice_3.mp3"
    old.write_bytes(b"old sound")
    a, b, c, d = _turns(client, 4)
    assert [_slot(client, t).json()["slot"] for t in (a, b)] == ["genpc_voice_1", "genpc_voice_2"]
    api.tts.fail = True
    r = _slot(client, c)
    assert r.status_code == 502
    assert old.read_bytes() == b"old sound"
    api.tts.fail = False
    assert _slot(client, d).json()["slot"] == "genpc_voice_4"


def test_empty_sound_is_a_failed_voice(env):
    """Rule 30j: the voice service sends nothing. The slot file keeps its old sound."""
    api, client, folder = env
    api.tts.stream = lambda text, voice_id: iter(())
    (folder / "genpc_voice_1.mp3").write_bytes(b"old sound")
    (tid,) = _turns(client, 1)
    assert _slot(client, tid).status_code == 502
    assert (folder / "genpc_voice_1.mp3").read_bytes() == b"old sound"


def test_cannot_write_gives_503_and_keeps_old_file(env, monkeypatch):
    """Rule 30m: the engine cannot write the slot file (example: the game has it open)."""
    api, client, folder = env
    old = folder / "genpc_voice_1.mp3"
    old.write_bytes(b"old sound")

    def locked(src, dst):
        raise PermissionError(13, "The file is in use")

    monkeypatch.setattr(api.os, "replace", locked)
    (tid,) = _turns(client, 1)
    r = _slot(client, tid)
    assert r.status_code == 503
    assert "genpc_voice_1.mp3" in r.json()["detail"] and "in use" in r.json()["detail"]
    assert old.read_bytes() == b"old sound"
    assert [p.name for p in folder.iterdir()] == ["genpc_voice_1.mp3"]  # the temp file is gone


def test_requests_at_the_same_time_get_different_slots(env):
    """Rule 30e: requests run at the same time (the route holds no lock during the voice call) and get
    different slot files. The voice calls wait for each other, so all three are in flight together."""
    api, client, folder = env
    ids = _turns(client, 3)
    api.tts.gate = threading.Barrier(3)
    out = []

    def go(t):
        out.append(_slot(client, t).json()["slot"])

    threads = [threading.Thread(target=go, args=(t,)) for t in ids]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=10)
    assert sorted(out) == ["genpc_voice_1", "genpc_voice_2", "genpc_voice_3"]


def test_slot_number_is_taken_under_its_lock(env, monkeypatch):
    """Rule 30e: each request takes its slot number while it holds `_slot_lock`."""
    api, client, folder = env
    seen = []

    class Recording:
        def __enter__(self):
            seen.append(("in", api._next_slot))

        def __exit__(self, *exc):
            seen.append(("out", api._next_slot))

    monkeypatch.setattr(api, "_slot_lock", Recording())
    for t in _turns(client, 2):
        _slot(client, t)
    assert seen == [("in", 0), ("out", 1), ("in", 1), ("out", 2)]


def test_start_again_uses_slot_1_first(env, tmp_path, monkeypatch):
    """Rule 30h: when the engine starts again, it uses slot file 1 first."""
    api, client, folder = env
    for t in _turns(client, 2):
        _slot(client, t)
    api = _load(tmp_path, monkeypatch)
    api._llm, api.tts = FakeLLM(), FakeTTS()
    client = TestClient(api.app)
    (tid,) = _turns(client, 1)
    assert _slot(client, tid).json()["slot"] == "genpc_voice_1"


def test_no_slot_file_cases(env, tmp_path, monkeypatch):
    """Rule 30i: 404 and no slot file changes (voice off, unknown turn, NPC with no voice)."""
    api, client, folder = env
    assert _slot(client, 9999).status_code == 404  # unknown turn
    crowd = {"entity_id": "1874320956", "name": "Dock worker", "settlement": "riverwood"}
    assert client.post("/api/npcs", json=crowd).status_code == 200
    (tid,) = _turns(client, 1, npc="crowd-1874320956")
    r = _slot(client, tid)
    assert r.status_code == 404 and "voice" in r.json()["detail"]  # the test world has no voice list
    api.tts = None  # the voice is off
    (tid,) = _turns(client, 1)
    assert _slot(client, tid).status_code == 404
    assert list(folder.iterdir()) == []


@pytest.mark.parametrize("slot_dir,make_dir,why", [(None, True, "AUDIO_SLOT_DIR"), ("missing", False, "not there")])
def test_no_slot_folder(tmp_path, monkeypatch, slot_dir, make_dir, why):
    """Rules 30i, 30l: no slot folder setting, or a folder that is not there. The engine does not make it."""
    api = _load(tmp_path, monkeypatch, slot_dir=slot_dir, make_dir=make_dir)
    api._llm, api.tts = FakeLLM(), FakeTTS()
    client = TestClient(api.app)
    (tid,) = _turns(client, 1)
    r = _slot(client, tid)
    assert r.status_code == 404 and why in r.json()["detail"]
    assert api.tts.calls == 0
    assert not (tmp_path / "missing").exists()
    assert client.post("/api/session/start").json()["capabilities"]["audio_slots"] == 0


def test_session_start_audio_slots(env, tmp_path, monkeypatch):
    """Session start gives `audio_slots`: the count when ready, 0 when the voice is off."""
    api, client, folder = env
    assert client.post("/api/session/start").json()["capabilities"]["audio_slots"] == 4
    api.tts = None
    assert client.post("/api/session/start").json()["capabilities"]["audio_slots"] == 0
    api = _load(tmp_path, monkeypatch, count="16")
    api.tts = FakeTTS()
    assert TestClient(api.app).post("/api/session/start").json()["capabilities"]["audio_slots"] == 16


@pytest.mark.parametrize("count", ["0", "17", "-1", "four", "2.5", ""])
def test_bad_slot_count_stops_the_engine(env, monkeypatch, count):
    """System overview: if AUDIO_SLOT_COUNT is not from 1 to 16, the engine does not start and tells why."""
    api, client, folder = env
    monkeypatch.setenv("AUDIO_SLOT_COUNT", count)
    with pytest.raises(RuntimeError, match="AUDIO_SLOT_COUNT"):
        api._slot_settings()


def test_tests_do_not_read_the_env_file(env, monkeypatch):
    """Regression: the tests must not read AUDIO_SLOT_DIR from the developer's `.env` (a real game folder)."""
    import dotenv

    assert dotenv.load_dotenv() is False


def test_stream_route_is_unchanged(env):
    """Rules 29, 30n: GET /api/audio still streams the voice and writes no slot file."""
    api, client, folder = env
    (tid,) = _turns(client, 1)
    r = client.get(f"/api/audio/{tid}")
    assert r.status_code == 200 and r.content.startswith(b"part1-")
    assert list(folder.iterdir()) == []
