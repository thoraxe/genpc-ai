"""M5 live eval: run the Embershard story N times per check against the real LLM.

Run: uv run python poc/scripts/eval.py [N]   (default 10)
Pass bars: innkeeper mentions the event >= 8/10; guard leaks dropped details 0/10; Solitude leaks 0/10.
Every line is printed so a human can skim for leaks the keyword checks miss.
"""

import json
import re
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "poc"))
sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(ROOT / ".env")

from engine.dialog import DialogEngine  # noqa: E402
from engine.models import Fact, WorldEvent  # noqa: E402
from engine.providers.llm import from_env  # noqa: E402
from engine.store import Store, load_events, load_world  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
WORLD = load_world(ROOT / "poc" / "data" / "world.json")
EV = load_events(ROOT / "poc" / "data" / "events.json")["embershard_cleared"]
LLM = from_env()

CHECKS = {
    # name: (npc, days after event, player question, regex, mode)  mode "hit" = must match, "leak" = must not match
    "innkeeper_knows": ("torvald", 0.5, "What's the news around here?", r"embershard|bandit", "hit"),
    "guard_vague": (
        "eirik",
        3.0,
        "What exactly happened at the mine? Who did it, how, and what did they take?",
        r"\baxe\b|\bdusk\b|evening|sunset|\bleader\b|chief|carried off|made off with|took (?:the|their|all) (?:loot|gold|treasure|coin)",
        "leak",
    ),
    "solitude_ignorant": (
        "sabine",
        3.0,
        "Heard anything about trouble near Riverwood lately?",
        r"embershard|\bsteel\b|cleared|bandits? (?:are|were) (?:dead|killed|slain)",
        "leak",
    ),
}


def run_once(check: str, i: int) -> dict:
    npc, after, question, pattern, mode = CHECKS[check]
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "e.db", WORLD, start_day=41.0)
        store.report_event(
            WorldEvent(
                id="ev1",
                type=EV["type"],
                location=EV["location"],
                day=41.0,
                facts=[Fact(**f) for f in EV["facts"]],
                witnesses=EV["default_witnesses"],
            )
        )
        store.advance(after)
        d = DialogEngine(store, LLM)
        t1 = d.open(npc)
        t2 = d.choose(t1.session_id, npc, question)
        store.db.close()
    text = f"{t1.npc_line} || {t2.npc_line}"
    matched = re.search(pattern, text, re.I)
    ok = bool(matched) if mode == "hit" else not matched
    return {
        "check": check,
        "i": i,
        "ok": ok,
        "match": matched.group(0) if matched else None,
        "fallback": t1.fallback or t2.fallback,
        "ms": [t1.llm_ms, t2.llm_ms],
        "text": text,
    }


def main():
    t0 = time.perf_counter()
    jobs = [(c, i) for c in CHECKS for i in range(N)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda j: run_once(*j), jobs))
    out = ROOT / "poc" / "var" / f"eval-{int(time.time())}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    bars = {
        "innkeeper_knows": lambda k: k >= round(0.8 * N),
        "guard_vague": lambda k: k == N,
        "solitude_ignorant": lambda k: k == N,
    }
    all_pass = True
    for c in CHECKS:
        rs = [r for r in results if r["check"] == c]
        k = sum(r["ok"] for r in rs)
        passed = bars[c](k)
        all_pass &= passed
        print(f"\n=== {c}: {k}/{N} ok -> {'PASS' if passed else 'FAIL'} (fallbacks: {sum(r['fallback'] for r in rs)})")
        for r in rs:
            flag = "  " if r["ok"] else "!!"
            extra = f" [matched: {r['match']}]" if r["match"] and not r["ok"] else ""
            print(f"{flag} {r['text']}{extra}")
    ms = [m for r in results for m in r["ms"] if m]
    q = statistics.quantiles(ms, n=20)
    print(
        f"\nLLM latency over {len(ms)} calls: p50={statistics.median(ms):.0f}ms p95={q[18]:.0f}ms max={max(ms):.0f}ms"
    )
    print(f"Total {time.perf_counter() - t0:.0f}s. Raw results: {out}")
    print(f"\nOVERALL: {'PASS' if all_pass else 'FAIL'}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
