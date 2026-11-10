# Project Structure

## Module Map

| File/Directory | Key Symbols | Responsibility |
|---|---|---|
| `poc/engine/models.py` | `Fact`, `Rules`, `WorldConfig`, `Settlement`, `Location`, `NPC`, `WorldEvent`, `Memory`, `MemoryView`, `Source`, `Stage` | Pydantic models. Game-neutral. `Rules` holds every knowledge tunable with its default; `WorldConfig.rules` lets the world file override them. |
| `poc/engine/knowledge.py` | `strength`, `view`, `event_settlement`, `witness_memories`, `due_rumors`, `retrieve`, `grounded`, `conversation_memory` | Pure, deterministic knowledge rules. No I/O, no LLM. See `knowledge-engine.md`. |
| `poc/engine/store.py` | `Store` (`advance`, `report_event`, `propagate`, `memories`, `mark_used`, `add_turn`, `turns`, `save`, `load`, `reset`), `load_world`, `load_events`, `STATE_TABLES` | SQLite persistence, the clock, rumor propagation trigger, save slots as whole-state JSON blobs. |
| `poc/engine/dialog.py` | `DialogEngine` (`open`, `choose`, `_turn`, `preview_prompt`), `build_system_prompt`, `_knowledge_block`, `DialogResponse`, `TurnResult`, `SOURCE_FRAMING`, `FALLBACK`, `GREETING` | One dialog turn: retrieve → prompt → LLM → validate/retry/fallback → memory write-back. See `dialog-pipeline.md`. |
| `poc/engine/providers/llm.py` | `LLMProvider` (Protocol), `OpenAICompatLLM`, `LLMResult`, `from_env` | OpenAI-compatible chat completions in JSON mode. z.ai by default; any provider via env. |
| `poc/engine/providers/tts.py` | `TTSProvider` (Protocol), `ElevenLabsTTS`, `from_env` | ElevenLabs streaming MP3. `from_env` returns `None` when disabled or keyless. |
| `poc/engine/api.py` | `app`, `store`, `world`, `presets`, `lock`, `dialog()`, `npc_or_404`, `_mem_json`, request models `Advance`/`EventIn`/`Open`/`Choose`/`SaveIn` | FastAPI routes (`what/http-api.md`). Module-level singletons built at import time from env. |
| `poc/data/world.json`, `poc/data/events.json` | — | The demo world and preset events (`what/world-file.md`). |
| `poc/ui/index.html` | `api()`, `refresh()`, `showTurn()` | Bare single-file test page. Only calls `/api/*`. Styling is deliberately bare (not worth reviewing). |
| `poc/tests/` | `test_knowledge.py`, `test_dialog.py`, `test_api.py` | Offline tests with a `FakeLLM`. See `testing-and-eval.md`. |
| `poc/scripts/eval.py` | `CHECKS`, `run_once`, pass bars | Live eval against the real LLM. |
| `poc/scripts/smoke.py`, `poc/scripts/live_dialog.py` | — | Manual provider smoke test and a live dialog run. |
| `.omc/plans/` | `npc-engine-plan.md`, `poc-python-ui-plan.md`, `cyberpunk-mod-plan.md` | Approved plans. The Cyberpunk plan maps to issues #1–#15. |
| `docs/` | — | Research: prior art, save-state feasibility, monetization. |
| `REVIEW.md` | — | Review priorities (knowledge leaks first). |
| `.github/` | `workflows/ci.yml`, `pull_request_template.md` | CI runs ruff + pytest and rejects PRs with empty template sections. |

## Key Entry Points

**Server:** `uv run uvicorn engine.api:app --app-dir poc --port 8000`. The import of `engine.api` does these steps:
1. It loads `.env`, the world file and the presets.
2. It opens the SQLite store. It makes `poc/var/` if necessary.
3. It builds the TTS provider.

The engine builds the LLM provider at the first dialog call (`dialog()`). Thus the server starts without an LLM key.

**Tests:** `uv run pytest -q`. `pyproject.toml` sets `pythonpath = ["poc"]`. Thus tests can import `engine.*`.

**Live eval:** `uv run python poc/scripts/eval.py 10`. It needs `.env`.

## Naming Conventions

- The code uses `settlement`, `location`, `hop1`/`hop2`, `gist`, `detailed`, `salience`, `mentioned` and `session`.
- The `what/` specs use plain words for the same things. `.ai/spec/glossary.md` gives the code name for each plain word.
- Do not rename code to match the plain words without an approved change. The API field names are an agreement with the mods.
- Memory sources: `witnessed`, `hop1` (same town), `hop2` (next town), `conversation` (from the player).
- Event ids from the API: `{preset or type}@{day:g}#{event count + 1}`.
- Branches: `feat/`, `fix/`, `docs/`, `chore/` (see `CLAUDE.md`).
