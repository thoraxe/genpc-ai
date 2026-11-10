# Testing and Eval

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `poc/tests/test_knowledge.py` | `store` fixture, `embershard()`, `facts_of()` | Deterministic scenarios: witnesses, hop1/hop2 timing and thresholds, far town, arrival-time creation, idempotency, decay stages, recall cap, save/load, grounding, news slots. |
| `poc/tests/test_dialog.py` | `FakeLLM(replies)`, `GOOD`, `SMALLTALK` | Prompt leak check, retry then success, fallback after two bad replies (no recall), provider error (no retry), news marking only when said, session history, setting text from the world file. |
| `poc/tests/test_api.py` | `FakeLLM`, `client` fixture | End-to-end API flow and input validation. Reloads `engine.api` with `POC_VAR_DIR`/`POC_DB` in `tmp_path` and `TTS_ENABLED=0`, then sets `api._llm`. |
| `poc/scripts/eval.py` | `CHECKS`, `run_once`, `main` | Live LLM eval: 3 checks × N runs, 4 threads, results in `poc/var/eval-*.json`. |

## Data Flow

- **Offline tests** build a `Store` on `tmp_path` with the real `poc/data/world.json` at `start_day=41.0`, then report the Embershard preset as `ev1`.
- **`FakeLLM`** in `test_dialog.py` pops scripted replies (dict → JSON string, raw string, or an `Exception` to raise) and records `(system, messages)` in `calls`, so tests can assert on the prompt.
- **Live eval** per run: fresh temp store → report Embershard on day 41 → advance → `open` + one `choose` → regex check on both lines.

| Check | NPC | Days after | Mode | Pass bar |
|---|---|---|---|---|
| `innkeeper_knows` | torvald | 0.5 | must match `embershard\|bandit` | ≥ 80% |
| `guard_vague` | eirik | 3.0 | must not mention axe, dusk, leader, loot | 100% |
| `solitude_ignorant` | sabine | 3.0 | must not mention Embershard, steel, cleared | 100% |

## Key Abstractions

- **Spec examples become tests.** Each example in an approved plain-language spec ("if the player does X, then Y") needs a test. Put knowledge examples in `test_knowledge.py`, prompt or turn examples in `test_dialog.py`, and route examples in `test_api.py`.
- **Every bug fix adds a regression test** (`CLAUDE.md`).
- **New prompt fields** need a test modelled on `test_prompt_contains_only_that_npcs_knowledge`.

## Implementation Notes

- Tests never touch the network. Do not import `providers.llm.from_env` in tests.
- The eval leak regexes can flag denials ("I don't know who took the loot") as leaks. This is issue #20. Read the printed lines before you trust a FAIL.
- The eval exits non-zero on failure; paste its summary in the PR when `knowledge.py` or the prompt/retrieval/validation in `dialog.py` changed.
