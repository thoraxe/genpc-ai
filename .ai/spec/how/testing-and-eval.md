# Testing and Eval

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `poc/tests/test_knowledge.py` | `store` fixture, `embershard()`, `facts_of()` | Fixed scenarios: witnesses, hop1/hop2 timing and thresholds, far town, arrival day, idempotency, decay stages, recall cap, save/load, grounding, news slots. |
| `poc/tests/test_dialog.py` | `FakeLLM(replies)`, `GOOD`, `SMALLTALK` | Prompt leak check, retry, fallback without recall, provider error without retry, news "told" only when said, session history, setting text. |
| `poc/tests/test_api.py` | `FakeLLM`, `client` fixture | API flow from start to end, and input checks. |
| `poc/tests/test_audio_slots.py` | `FakeTTS`, `_load`, `env` fixture | Slot files: rotation, failures keep the old sound, `503` on a locked file, requests at the same time, restart, settings. |
| `poc/scripts/eval.py` | `CHECKS`, `run_once`, `main` | Live LLM eval: 3 checks × N runs on 4 threads. Results go to `poc/var/eval-*.json`. |

## Data Flow

**Offline tests**
- The tests build a `Store` in `tmp_path`. They use the real `poc/data/world.json` with `start_day=41.0`.
- They report the Embershard preset as event `ev1`.
- `FakeLLM` in `test_dialog.py` gives scripted replies in order. A reply can be a dict (sent as JSON), a raw string, or an `Exception` (raised).
- `FakeLLM` records each `(system, messages)` in `calls`. Thus tests can check the prompt.
- `test_api.py` reloads `engine.api` with `POC_VAR_DIR` and `POC_DB` in `tmp_path` and `TTS_ENABLED=0`. Then it sets `api._llm` to its `FakeLLM`.
- `test_audio_slots.py` reloads `engine.api` with `AUDIO_SLOT_DIR` in `tmp_path`, then sets `api.tts` to a `FakeTTS` that sends the sound in two parts. `FakeTTS.gate` (a `threading.Barrier`) holds calls so that requests arrive at the same time.

**Live eval** (one run)
1. Make a new store in a temp folder.
2. Report Embershard on day 41.
3. Move the clock forward.
4. Call `open`, then one `choose`.
5. Check both lines with a regex.

| Check | NPC | Days after | Mode | Pass bar |
|---|---|---|---|---|
| `innkeeper_knows` | torvald | 0.5 | must match `embershard\|bandit` | 80% or more |
| `guard_vague` | eirik | 3.0 | must not match axe, dusk, evening, sunset, leader, chief, "carried off", "made off with", "took the/their/all loot/gold/treasure/coin" | 100% |
| `solitude_ignorant` | sabine | 3.0 | must not match Embershard, steel, cleared, "bandits are/were dead/killed/slain" | 100% |

The exact patterns are in `CHECKS` in `poc/scripts/eval.py`.

## Key Abstractions

- **Each spec example becomes a test.** An approved spec has examples ("if the player does X, then Y"). Each example needs a test.
  - Knowledge examples go in `test_knowledge.py`.
  - Prompt and turn examples go in `test_dialog.py`.
  - Route examples go in `test_api.py`.
- **Each bug fix adds a regression test** (`CLAUDE.md`).
- **Each new prompt field needs a leak test.** Use `test_prompt_contains_only_that_npcs_knowledge` as the model.

## Implementation Notes

- Tests never use the network. Do not import `providers.llm.from_env` in tests.
- The eval regexes can count a denial as a leak, for example "I don't know who took the loot". This is issue #20. Read the printed lines before you trust a FAIL.
- The eval exits with a non-zero code if a check fails.
- Paste the eval summary in the PR if you changed `knowledge.py`, or the prompt, retrieval or validation in `dialog.py`.
