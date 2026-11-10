"""M2 live check: run the Embershard story against the real LLM and print lines + latency.

Run: uv run python poc/scripts/live_dialog.py
Uses a throwaway DB in poc/var/.
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "poc"))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(ROOT / ".env")
logging.basicConfig(level=logging.WARNING)

from engine.dialog import DialogEngine  # noqa: E402
from engine.models import Fact, WorldEvent  # noqa: E402
from engine.providers.llm import from_env  # noqa: E402
from engine.store import Store, load_events, load_world  # noqa: E402

db = ROOT / "poc" / "var" / "live.db"
db.parent.mkdir(parents=True, exist_ok=True)
db.unlink(missing_ok=True)
store = Store(db, load_world(ROOT / "poc" / "data" / "world.json"), start_day=41.0)
llm = from_env()
d = DialogEngine(store, llm)
print(f"LLM: {llm.name}\n")


def talk(npc_id, follow_up=None):
    t = d.open(npc_id)
    print(f"[day {store.day:g}] {npc_id}: {t.npc_line}")
    print(f"    choices={t.choices}  llm={t.llm_ms:.0f}ms attempts={t.attempts} fallback={t.fallback}")
    if follow_up:
        t2 = d.choose(t.session_id, npc_id, follow_up)
        print(f"    PLAYER: {follow_up}")
        print(f"    {npc_id}: {t2.npc_line}")
        print(
            f"    choices={t2.choices}  llm={t2.llm_ms:.0f}ms remembered={[f.text for f in t2.remembered]} rejected={t2.rejected}"
        )
    print()
    return t


e = load_events(ROOT / "poc" / "data" / "events.json")["embershard_cleared"]
store.report_event(
    WorldEvent(
        id="ev1",
        type=e["type"],
        location=e["location"],
        day=41.0,
        facts=[Fact(**f) for f in e["facts"]],
        witnesses=e["default_witnesses"],
    )
)
talk("hrolf")
store.advance(0.5)
talk("torvald", "Yes, that was me. I'm Aela, and I'm saving up to buy a horse.")
store.advance(2.5)
talk("eirik", "What did the stranger take from the mine?")
talk("sabine", "Any news from Riverwood?")
store.advance(3)
talk("torvald", "Do you remember me?")
