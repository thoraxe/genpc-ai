"""The mod's own files (mod spec what/talk.md). Offline: these tests read the files; the game is not needed.

The in-game behaviour is checked by the owner's in-game test (PR #43). These tests catch file mistakes early.
"""

import json
import re
import sys
from pathlib import Path

MOD = Path(__file__).resolve().parents[1]
SCRIPTS = MOD / "r6" / "scripts" / "genpc"
AUDIO = MOD / "r6" / "audioware" / "genpc"
sys.path.insert(0, str(MOD / "tools"))

import world_reds  # noqa: E402

# Owner question 2 on PR #43: the story characters.
STORY = [
    "Jackie Welles",
    "Judy Alvarez",
    "Panam Palmer",
    "Johnny Silverhand",
    "Goro Takemura",
    "River Ward",
    "Kerry Eurodyne",
    "Viktor Vektor",
    "Misty Olszewski",
    "Evelyn Parker",
    "Dexter DeShawn",
    "Rogue Amendiares",
    "Alt Cunningham",
    "Saul Bright",
    "Mitch Anderson",
    "Lizzy Wizzy",
    "Hanako Arasaka",
]


def test_world_script_matches_world_file():
    # world.md rule 12: the mod sends world.json. Run tools/world_reds.py after each change of world.json.
    expected = world_reds.render((MOD / "world.json").read_text(encoding="utf-8"))
    assert (SCRIPTS / "World.reds").read_text(encoding="utf-8") == expected


def test_world_script_round_trip():
    # The text in the script is the same JSON as world.json, after redscript reads the string.
    text = (SCRIPTS / "World.reds").read_text(encoding="utf-8")
    literal = re.search(r'return "(.*)";', text).group(1)
    unescaped = literal.replace('\\"', '"').replace("\\\\", "\\")
    assert json.loads(unescaped) == json.loads((MOD / "world.json").read_text(encoding="utf-8"))


def test_four_slot_files():
    # talk.md rule 17b: 4 slot names; engine http-api.md rule 30c: genpc_voice_1.mp3 to genpc_voice_4.mp3.
    manifest = (AUDIO / "genpc.yml").read_text(encoding="utf-8")
    for n in range(1, 5):
        assert f"genpc_voice_{n}:\n    file: genpc_voice_{n}.mp3\n    usage: on-demand" in manifest
        assert (AUDIO / f"genpc_voice_{n}.mp3").stat().st_size > 0  # the sound tool needs the files at start
    assert "genpc_voice_5" not in manifest


def test_story_characters():
    # talk.md rule 11.
    npc = (SCRIPTS / "Npc.reds").read_text(encoding="utf-8")
    block = npc[npc.index("func IsStoryCharacter") : npc.index("];", npc.index("func IsStoryCharacter"))]
    assert re.findall(r'"([^"]+)"', block) == STORY


def test_every_cast_npc_is_found():
    # talk.md rule 9: each NPC of the starter cast maps to its world-file id.
    npc = (SCRIPTS / "Npc.reds").read_text(encoding="utf-8")
    block = npc[npc.index("func CastId") : npc.index("default:", npc.index("func CastId"))]
    pairs = dict(re.findall(r'case "([^"]+)": return "([^"]+)";', block))
    world = json.loads((MOD / "world.json").read_text(encoding="utf-8"))
    assert set(pairs.values()) == {n["id"] for n in world["npcs"]}
    for n in world["npcs"]:
        if not n["name"].startswith(("Sebastian", "Muamar")):
            assert pairs[n["name"]] == n["id"]
    assert not set(pairs) & {s for full in STORY for s in (full, full.split()[0])}


def test_rules_in_code():
    # The numbers of the approved rules.
    system = (SCRIPTS / "System.reds").read_text(encoding="utf-8")
    npc = (SCRIPTS / "Npc.reds").read_text(encoding="utf-8")
    assert "> 4.0" in system  # rule 6
    assert 'Equals(this.Refusal(npc, player, GenpcNpc.Name(npc)), "-")' in system  # rule 5d: the same checks
    assert "> 8.0" in system  # rule 24
    assert "this.StartTimeout(3.0)" in system  # rule 2
    assert system.count("this.StartTimeout(60.0)") == 2  # rule 28
    assert '"Stranger"' in npc and "StrLen(name) > 60" in npc  # rules 12a, 12b
    assert 'this.lastTown = "watson";  // rule 13b' in system
    assert "SetMaxLength(500)" in (SCRIPTS / "Panel.reds").read_text(encoding="utf-8")  # rule 20c
    assert "http://localhost:8000" in system  # constraint


def test_own_weapon_block():
    # talk.md rule 19a. The mod's own record, so a load can always remove it, and the game's NoWeapons stays.
    tweak = (MOD / "r6" / "tweaks" / "genpc.yaml").read_text(encoding="utf-8")
    assert "Genpc.NoWeapons:\n  $base: GameplayRestriction.NoWeapons" in tweak
    system = (SCRIPTS / "System.reds").read_text(encoding="utf-8")
    assert "GameplayRestriction.NoWeapons" not in system
    assert system.count('t"Genpc.NoWeapons"') == 3  # apply, remove, remove after each load


def test_no_secret_in_mod():
    # talk.md rule 32: the mod does not read .env.
    for f in SCRIPTS.glob("*.reds"):
        text = f.read_text(encoding="utf-8")
        assert ".env" not in text and "API_KEY" not in text


def test_refusal_reason_is_logged():
    # PR #43 test: the janitor said "Not now." with no way to see why. The log now names the exact reason.
    system = (SCRIPTS / "System.reds").read_text(encoding="utf-8")
    for why in ("down", "far", "hostile", "combat", "vehicle", "scene", "dialogue", "story"):
        assert f'return "{why}";' in system
    assert "[genpc] cannot talk to " in system


def test_text_key_is_not_a_name():
    # PR #43 test: a crowd NPC showed "NCResident". Rule 12: the shown text if the game has one, else "Stranger".
    npc = (SCRIPTS / "Npc.reds").read_text(encoding="utf-8")
    assert "GetLocalizedTextByKey(StringToName(name))" in npc
    assert "GenpcNpc.IsKey(name)" in npc
    # 2nd test: "Sandra Dorsett" became "Stranger". Only a key is looked up.
    assert npc.index("if GenpcNpc.IsKey(name) {") < npc.index("GetLocalizedTextByKey")
