"""The game sets the clock from its hours (spec #9: saves-and-clock.md rules 5a-5g, http-api.md rules 10a-10e,
world-file.md rules 1a-1b). Offline: a fake LLM and no TTS."""

import copy
import importlib

import pytest
from fastapi.testclient import TestClient

DAY30 = {  # a made-up mod world with 30-hour days that starts at day 0
    "id": "long_days",
    "start_day": 0,
    "calendar": {"hours_per_day": 30},
    "settlements": [{"id": "town", "name": "Town"}],
    "npcs": [{"id": "ana", "name": "Ana", "role": "baker", "settlement": "town", "bio": "Bakes bread."}],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("POC_VAR_DIR", str(tmp_path))
    monkeypatch.setenv("POC_DB", str(tmp_path / "test-world.db"))
    monkeypatch.setenv("TTS_ENABLED", "0")
    import engine.api as api

    return TestClient(importlib.reload(api).app)


def set_hours(client, hours):
    return client.post("/api/clock/set", json={"hours": hours})


def day(client):
    return client.get("/api/world").json()["day"]


def embershard(client):
    r = client.post("/api/events", json={"preset": "embershard_cleared", "witnesses": ["hrolf"]})
    assert r.status_code == 200


# ---------- Summary examples 1-6 (test world: 24-hour days, starts at day 41 = hour 984) ----------
def test_example_1_later_hours_move_the_clock_and_bring_gossip(client):
    embershard(client)
    r = set_hours(client, 996)
    assert r.status_code == 200
    assert r.json()["day"] == pytest.approx(41.5)
    assert "torvald" in {m["npc_id"] for m in r.json()["new_memories"]}


def test_example_2_the_same_hours_again_change_nothing(client):
    embershard(client)
    set_hours(client, 996)
    r = set_hours(client, 996)
    assert r.status_code == 200
    assert r.json() == {"day": pytest.approx(41.5), "new_memories": []}


def test_example_3_earlier_hours_are_refused_and_the_answer_gives_the_day(client):
    set_hours(client, 996)
    r = set_hours(client, 984)
    assert r.status_code == 400
    assert r.json()["detail"]["day"] == pytest.approx(41.5)
    assert day(client) == pytest.approx(41.5)


def test_example_4_load_the_save_first_then_set_the_clock(client):
    save_id = client.post("/api/saves", json={"label": "day 41"}).json()["id"]
    set_hours(client, 996)
    client.post(f"/api/saves/{save_id}/load")
    r = set_hours(client, 984)
    assert r.status_code == 200
    assert r.json() == {"day": pytest.approx(41), "new_memories": []}


def test_example_5_negative_hours_are_refused(client):
    r = set_hours(client, -5)
    assert r.status_code == 400
    assert r.json()["detail"]["day"] == 41
    assert day(client) == 41


def test_example_6_more_than_365_days_is_refused_but_365_is_accepted(client):
    r = set_hours(client, 9768)  # day 407, 366 days later
    assert r.status_code == 400 and day(client) == 41
    assert set_hours(client, (41 + 365) * 24).status_code == 200
    assert day(client) == pytest.approx(406)


# ---------- Summary examples 7-8 and world-file.md rules 1a-1b: the length of a day ----------
def test_example_7_a_world_with_30_hour_days(client):
    assert client.post("/api/world", json=DAY30).status_code == 200
    r = set_hours(client, 900)
    assert r.status_code == 200 and r.json()["day"] == pytest.approx(30)


@pytest.mark.parametrize("hours_per_day", [0, -24])
def test_example_8_a_day_length_of_0_or_less_is_refused(client, hours_per_day):
    bad = copy.deepcopy(DAY30)
    bad["calendar"]["hours_per_day"] = hours_per_day
    r = client.post("/api/world", json=bad)
    assert r.status_code == 400
    assert "hours_per_day" in r.json()["detail"]


def test_a_world_without_a_calendar_has_24_hour_days(client):
    w = copy.deepcopy(DAY30)
    w.pop("calendar")
    client.post("/api/world", json=w)
    assert set_hours(client, 48).json()["day"] == pytest.approx(2)


# ---------- rule 5g and its example: start day 0 ----------
def test_a_new_game_at_start_day_0(client):
    client.post("/api/world", json=DAY30 | {"calendar": {"hours_per_day": 24}})
    assert day(client) == 0
    r = set_hours(client, 5)
    assert r.status_code == 200 and r.json()["day"] == pytest.approx(5 / 24)


# ---------- world-file.md rule 16k, owner question 4: a new day length ----------
def test_a_new_day_length_applies_to_the_next_hours(client):
    client.post("/api/world", json=DAY30 | {"calendar": {"hours_per_day": 24}})
    set_hours(client, 996)  # day 41.5
    client.post("/api/world", json=DAY30)  # same world, now 30-hour days
    assert day(client) == pytest.approx(41.5)  # the clock keeps its day
    assert set_hours(client, 996).status_code == 400  # 996 / 30 = 33.2 is earlier: the clock waits
    assert set_hours(client, 1260).json()["day"] == pytest.approx(42)  # 1260 / 30 = 42


# ---------- http-api.md rule 4a: wrong types ----------
def test_missing_or_wrong_hours_is_422(client):
    assert client.post("/api/clock/set", json={}).status_code == 422
    assert client.post("/api/clock/set", json={"hours": "soon"}).status_code == 422


# ---------- review fixes: non-numbers and the 365-day edge ----------
@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_hours_that_are_not_a_real_number_are_400_with_the_day(client, raw):
    r = client.post("/api/clock/set", content=f'{{"hours": {raw}}}', headers={"content-type": "application/json"})
    assert r.status_code == 400
    assert r.json()["detail"]["day"] == 41
    assert day(client) == 41


def test_exactly_365_days_from_an_uneven_clock_is_accepted(client):
    set_hours(client, 41.1 * 24)
    assert set_hours(client, (41.1 + 365) * 24).status_code == 200
