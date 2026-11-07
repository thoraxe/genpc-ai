# PoC Plan: NPC Knowledge Engine, Python + simple web UI (no game)

Status: **IN PROGRESS: M0 done** (see Progress log) · 2026-11-07 · Parent plan: `npc-engine-plan.md`. This is a slice of Phase 1 and Phase 2, with the UI standing in for the game.

## Goal
Show the novel part, the deterministic knowledge model, working end to end in a browser:
- **Event:** clear the bandits at Embershard Mine.
- **Gossip:** the news spreads with detail lost at each hop.
- **Conversation:** NPCs talk about what they know, with a voiced reply and 3 generated choices.
- **Memory:** it fades over in-game days.
- **Saves:** "loading an older save" rolls back what NPCs know.

The UI acts as a game client against the same HTTP API a mod would call. That makes it the first proof that the API is game-neutral (AC-F).

## Non-goals
Any game integration · lip-sync · co-save · relationship graph · multiple LLM providers in use (the interface exists, with one implementation) · auth · deployment · polish.

## Stack
- **Engine:** Python ≥3.12, managed with **uv**:
  - `pyproject.toml` + `uv.lock` at the repo root;
  - uv picked CPython 3.14.3;
  - run everything with `uv run`.
- **Libraries:** FastAPI, uvicorn, SQLite (stdlib `sqlite3`), pydantic v2, `openai` SDK, `httpx`, `python-dotenv`, pytest (dev).
- **UI:** one static `index.html` with vanilla JS, served by FastAPI. No build step.

## Providers (checked against docs, 2026-11-07)
- **LLM: z.ai, through its OpenAI-compatible API.**
  - Settings (verified in M0):
    - `ZAI_BASE_URL` defaults to `https://api.z.ai/api/coding/paas/v4/`, because the current key is a **Coding Plan** key.
      - A Coding Plan key gets `1113 insufficient balance` on the standard `/api/paas/v4/` endpoint.
      - A standard key would use `/api/paas/v4/`.
    - Model `glm-5.3-flash` by default, configurable (`glm-5.3` for quality).
    - `reasoning_effort="low"`.
      - GLM-5.3 models **cannot** disable thinking: `thinking.type=disabled` returns a 400.
      - `thinking={"type":"enabled","effort":"low"}` still produced about 2.5k reasoning characters and took about 10 s.
  - **Key caveat:** since 2026-10-16, z.ai manages standard API keys and GLM Coding Plan keys separately.
    - The Coding Plan is meant for coding tools, so using it for NPC dialog may conflict with its terms.
    - That's acceptable for local testing. Move to a standard key (an endpoint change only) before anything public.
  - **Structured output:** `response_format={"type":"json_object"}`, meaning JSON mode with no schema enforcement. So we validate with pydantic, retry once on failure, then use an in-character fallback line.
- **TTS: ElevenLabs.**
  - z.ai's API lists speech-to-text (GLM-ASR) but **no text-to-speech**.
  - Use the streaming TTS endpoint (`/v1/text-to-speech/{voice_id}/stream`) with `eleven_flash_v2_5` (configurable), one `voice_id` per NPC.
  - The key needs the `voices_read` permission to list voices. It now has it, and 29 voices are available.
  - Voice candidates:

    | NPC | Voice | voice_id |
    |---|---|---|
    | Guard | Harry, "Fierce Warrior" | `SOYHLrjzK2X1ezoPC6cr` |
    | Innkeeper | George, "Warm Storyteller" | `JBFqnCBsd6RMkjVDRZzb` |
    | Miner | Callum, "Husky Trickster" | `N2lVS1w4EtoT3dr4eOWO` |
  - Output is MP3, streamed through the engine to the browser `<audio>`.
  - Audio is cached by `(voice_id, text)` hash to save quota.
  - A voice on/off toggle in the UI.
- **Secrets:** `.env` holds `ZAI_API_KEY` and `ELEVENLABS_API_KEY`. `.env` is gitignored, and keys are redacted from logs.

## Repo layout
```
poc/
  engine/
    models.py      # pydantic: NPC, Fact, WorldEvent, Memory, Turn, DialogResponse
    store.py       # SQLite schema + snapshot/restore (fake "save slots")
    knowledge.py   # witnesses, propagation (hops), decay, gist, retrieval
    dialog.py      # prompt builder, LLM call, validation, memory write-back
    providers/llm.py, providers/tts.py   # Protocols + ZaiLLM, ElevenLabsTTS
    api.py         # FastAPI routes
  data/world.json  # settlements, adjacency, NPCs (bio, location, voice_id)
  data/events.json # preset events (Embershard cleared, + 1 more)
  ui/index.html
  tests/           # deterministic tests: no network
  scripts/smoke.py # M0 provider check
```

## Engine rules (defaults from parent plan §1, all in config)
- **Events:**
  - An event has facts with importance 1–5, plus a list of witnesses.
  - Witnesses get every fact at salience 1.0.
- **Propagation:** runs on each clock advance.
  - **Hop 1:** same settlement, after 0.5 days. Facts with importance below 3 are dropped; salience 0.8.
  - **Hop 2:** neighbouring hold, after 3 days. Facts below 4 are dropped; salience 0.6.
  - Nothing goes further.
- **Decay:** `strength = salience · e^(−0.08·Δdays) · (1 + min(0.5, 0.25·recalls))`.
  - Below 0.35, the memory becomes a gist: only facts with importance ≥3 are kept.
  - Below 0.05, it's forgotten.
- **Retrieval:** top-k memories by strength, plus a "recent news" slot (≤2 items under 3 days old that haven't been mentioned to the player yet).
- **Conversation memory:**
  - The LLM's JSON includes `remember: [{fact, importance}]`.
  - The engine keeps a fact only if it passes the grounding check: its key terms must appear in the transcript.
- **Prompt contents:** only the bio and the retrieved facts, plus an instruction never to invent world events. This is the "knows nothing" guarantee.

## API (game-neutral)
| Route | Purpose |
|---|---|
| `POST /session/start` | Capabilities (max_choices, audio format) |
| `GET /world` | NPCs, clock, saves |
| `POST /clock/advance {days}` | Advance time; runs propagation + decay |
| `POST /events {type, facts, witnesses, location}` | Report an event (UI uses presets) |
| `POST /dialog/open {npc_id}` → `{turn_id, npc_line, choices[]}` | Start a conversation |
| `POST /dialog/choose {turn_id, choice_idx \| text}` | Next turn |
| `GET /audio/{turn_id}` | Streamed MP3 |
| `GET /npc/{id}/knowledge` | Inspector data (memories, strength, facts kept/lost, hop) |
| `POST /saves` / `POST /saves/{id}/load` | Snapshot and restore the SQLite state |

## UI (single page, three columns)
1. **World:**
   - the clock (day 41.0);
   - `+0.5d` `+1d` `+7d` `+30d` buttons;
   - preset event buttons with witness checkboxes;
   - Save / Load save-slot buttons;
   - the event log.
2. **Talk:**
   - NPC list grouped by settlement;
   - the dialog pane: the NPC line appears as soon as it arrives and the audio plays as it streams;
   - 3 choice buttons plus an optional text box.
3. **Inspector (the money shot):** the selected NPC's memories, each showing:
   - a strength bar;
   - a source badge (witnessed, hop 1 or hop 2);
   - its facts, with dropped and gisted facts struck through.

This makes "deterministic, lossy gossip" visible instead of something you have to take on trust.

## Milestones (part-time estimates)
| # | Deliverable | Est. | Done when |
|---|---|---|---|
| M0 | Project skeleton, `.env`, `scripts/smoke.py` calling z.ai (JSON mode) and ElevenLabs (one MP3) | 0.5 d | Both calls succeed; time to first token and to first audio byte printed |
| M1 | models, store, knowledge + pytest (no LLM) | 2–3 d | Scenario tests below pass offline |
| M2 | dialog.py + ZaiLLM: prompt, JSON validation/retry, fallback, memory write-back | 1 d | Reply under 3 s typically with Flash; invalid JSON handled |
| M3 | ElevenLabsTTS streaming + cache + voice toggle | 0.5 d | Audio starts under 1.5 s after text appears |
| M4 | UI (three columns) on the API | 1–2 d | Whole demo clickable without a terminal |
| M5 | Save slots + demo script (`DEMO.md`) + live eval script | 0.5–1 d | Checks below pass |

**Total: about 6–8 working days, part-time.**
- If the JSON call is too slow, M2 can split into two calls: stream the line as plain text, then fetch the choices.
- Only do that if M0's timings say so.

## Acceptance checks
**Deterministic (pytest, M1):**
1. Day 41, Embershard cleared with the miner as witness.
   - **Day 41.5:** the innkeeper has facts with importance ≥3 at hop 1.
   - **Day 44:** the Whiterun guard has facts ≥4 at hop 2.
   - **Solitude NPC:** has no Embershard facts at any time.
2. A conversation memory is still detailed at +3 days, gist only at +30 days, and gone at about +37 days with no recall.
3. Save at day 41, advance to day 44, load the save: the guard has no Embershard memory again.
4. Grounding: a `remember` fact that isn't in the transcript is rejected.

**Live (scripts/eval.py, M5; 10 runs each):**
- The innkeeper mentions the mine or bandits in at least 8 of 10 runs.
- The guard's line never mentions the loot or the axe (0 of 10).
- The Solitude NPC never mentions the event (0 of 10).
- Checked by keyword matching, plus a manual skim.

## Risks
| Risk | Mitigation |
|---|---|
| z.ai key type or endpoint mismatch (Coding Plan vs standard) | **Resolved in M0:** Coding Plan endpoint plus `reasoning_effort=low`. The endpoint is config, so any OpenAI-compatible provider can be swapped in |
| Coding Plan terms (meant for coding tools) | Local testing only; switch to a standard key before sharing or hosting |
| JSON mode without a schema returns malformed choices | pydantic validation, 1 retry, in-character fallback, and logging of failure rate |
| GLM latency or availability outside China-region routing | Measure in M0; Flash model; thinking disabled |
| ElevenLabs quota burn while iterating | Audio cache, voice toggle, short lines (≤2 sentences) |
| LLM brings in Skyrim lore it already knows | Original NPC names and settlements are allowed if needed; the prompt bans invented events; the live eval measures it |

## Progress log
**2026-11-07, M0 done.**
- **Setup:**
  - `uv init` project: `pyproject.toml`, `uv.lock`, `.venv/`.
  - `.gitignore` covers `.env`, `*.swp`, `.venv/` and `poc/var/`.
  - `poc/scripts/smoke.py`: one z.ai JSON-mode call and one ElevenLabs streamed TTS call, with timings. It never prints keys and forces UTF-8 output for z.ai's Chinese error messages.
- **Results** (`uv run python poc/scripts/smoke.py` → `RESULT zai=OK elevenlabs=OK`):
  - **z.ai `glm-5.3-flash`:** 1.93 s total, valid JSON, about 50 completion tokens, 4 of them reasoning. Sample reply: `"Sit, drink, or leave—your pick."` with 3 choices.
  - **z.ai `glm-5.3`:** about 2.35 s.
  - **ElevenLabs `eleven_flash_v2_5`:** first byte in 0.15 s, total 0.21 s, about 55 KB MP3 at `poc/var/smoke.mp3`.
  - **Implication:** LLM time plus first audio byte is about 2.1 s, inside the 3 s target, so **the single JSON call is kept**. The two-call streaming split isn't needed unless real prompts with memories push it past 3 s; re-measure in M2.
- **Issues hit and fixed:**
  1. The first two z.ai keys returned `401 / 1000 Authentication Failed` on every endpoint. A freshly created key fixed it.
  2. The ElevenLabs key lacked `voices_read`. The user added the permission.
  3. GLM-5.3 rejects `thinking.type=disabled`, so `reasoning_effort="low"` is used instead.
  4. The new key on the standard endpoint returned `1113 insufficient balance`. Switched to the Coding Plan endpoint.
  5. The Windows console (cp1252) crashed printing z.ai's Chinese error. Fixed with `sys.stdout.reconfigure(encoding="utf-8")`.

**2026-11-07, M1 done.** `uv run pytest -q` → **11 passed** (about 1.5 s, no network).
- **`poc/engine/models.py`:** `Fact`, `Rules` (every tunable, with the parent plan's defaults), `Settlement`/`Location`/`NPC`/`WorldConfig`, `WorldEvent`, `Memory`, `MemoryView`.
- **`poc/engine/knowledge.py`:** pure rules.
  - `strength`/`view`: decay → detailed/gist/forgotten, with kept and dropped facts.
  - `witness_memories`, `due_rumors`: hop 1 to the same settlement, hop 2 to adjacent settlements, nothing further. A rumor is dated by its **arrival** time, so one big time jump gives the same result as many small ones.
  - `retrieve`: top-k plus the news slot.
  - `grounded`/`conversation_memory`: at least 50% of a fact's key terms must appear in the transcript.
- **`poc/engine/store.py`:** SQLite (meta/events/memories/turns).
  - `advance()` runs propagation; time only moves forward.
  - `report_event()` is idempotent by event id.
  - `mark_used()` adds a recall and marks news as mentioned.
  - Save slots snapshot the whole state into a `saves` table; `load()` restores it.
- **`poc/data/world.json`:**
  - Settlements: Riverwood ↔ Whiterun are adjacent; Solitude is isolated. The location `embershard_mine` is near Riverwood.
  - 4 NPCs:

    | NPC | Role | Voice |
    |---|---|---|
    | Hrolf | miner, witness | Callum |
    | Torvald | innkeeper | George |
    | Eirik | Whiterun guard | Harry |
    | Sabine | Solitude merchant | Sarah |
- **`poc/data/events.json`:** `embershard_cleared` (5 facts, importance 5…1) and `riverwood_wolf`.
- **`poc/tests/test_knowledge.py`** covers:
  - the witness getting every fact;
  - hop 1 at exactly +0.5 days with importance ≥3;
  - hop 2 at exactly +3 days with ≥4 only (no loot, no axe);
  - Solitude never hearing anything, even after 30 days;
  - arrival-time dating;
  - idempotent reporting;
  - conversation memory detailed at +3 days, gist at +30 and forgotten at +38;
  - the recall cap (gist at 30 days, forgotten at 43);
  - save → advance → load rolling back, and a replay re-deriving the same rumors;
  - grounding rejecting invented facts;
  - the news slot beating stronger memories, then clearing once mentioned.
- **Config:** `pyproject.toml` gained `[tool.pytest.ini_options]` (pythonpath `poc`).

**2026-11-07, M2 done.** `uv run pytest -q` → **16 passed**. Live run: `uv run python poc/scripts/live_dialog.py`.
- **`poc/engine/providers/llm.py`:** an `LLMProvider` Protocol and `OpenAICompatLLM`.
  - Configured by env: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY_ENV`, `LLM_REASONING_EFFORT`.
  - Defaults: z.ai Coding Plan endpoint, `glm-5.3-flash`, `reasoning_effort=low`, timeout 20 s, no SDK retries.
- **`poc/engine/dialog.py`:** `DialogEngine.open/choose`.
  - **Prompt:** the bio plus **only** the retrieved facts. Each fact is framed by its source (saw it / heard in town / travelers' rumor / the player told you), with gist memories flagged as vague and fresh news tagged.
  - **Rules in the prompt:** never invent events, and sound uncertain when the knowledge is secondhand.
  - **Validation:** pydantic `DialogResponse` (exactly 3 choices). One retry on bad JSON, then a fallback line. A provider error goes straight to the fallback.
  - **Write-back:** `remember` facts are grounded against the **player's** lines only.
  - **Bookkeeping:** a delivered turn counts as a recall and marks any news shown as mentioned. Fallback turns change nothing.
  - **Sessions:** the first turn's id is the session id, and the session history is replayed as messages.
- **`poc/tests/test_dialog.py`** (fake LLM), 5 tests:
  - Sabine's prompt has no Embershard facts;
  - Eirik's prompt has no loot, axe or dusk;
  - retry then success;
  - fallback with no recall changes;
  - a provider error gives an immediate fallback;
  - news marking, session history, and a grounded fact accepted while an invented "dragon slayer" fact is rejected.
- **Bug found by the tests and fixed:** replayed history dropped the opening turn's user message, so the history began with an assistant message.
- **Live results** (glm-5.3-flash), all on-model:
  - **Hrolf (witness):** full detail: steel armor, dusk, the leader.
  - **Torvald (day 41.5, hop 1):** raises the news unprompted. After the player reveals themselves he mentions the loot, and he stores "Player is Aela… saving up for a horse".
  - **Eirik (day 44, hop 2):** "Heard someone in steel cleared out the bandits." Asked what was taken: "Couldn't tell you. I only heard the bandits were killed and the stranger wore steel." **Correctly vague.**
  - **Sabine (Solitude):** "I've heard nothing worth repeating." **No leak.**
  - **Torvald (day 47):** greets Aela by name and remembers the horse. The duplicate "Player is Aela" was rejected as ungrounded, which was correct.
  - **Latency** (LLM only): 1.9–3.1 s, median about 2.1 s. Follow-up turns with history run slightly slower. With TTS's 0.15 s first byte this is about at the 3 s target. **The two-call split is not needed yet.** Revisit if the median creeps past 2.8 s.
  - **Minor embellishment seen:** "Half of Riverwood's still talking about it". It isn't an invented event, so it's acceptable for the PoC. The M5 eval keyword checks will watch for this.

**Next: M3** (ElevenLabs streaming TTS, audio cache, voice toggle).

## Afterwards (not in this plan)
Two-call streaming pipeline if needed · second LLM provider (AC-G) · Skyrim text+voice client against the same API (engine-played audio, no lip-sync) · co-save snapshot.
