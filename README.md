# genpc-ai

*Temporary name.* A game-agnostic engine for generative-AI NPCs whose knowledge is consistent.

Most AI-NPC mods give every character the same all-knowing language model. This project puts a **deterministic knowledge model** in front of the LLM instead:
- **Who knows what:** NPCs know what they saw. News reaches others as gossip, which arrives later and loses detail with every retelling.
- **Memories fade** over in-game time, down to a gist and then to nothing.
- **Knowledge follows the save file.** Loading an earlier save rolls back what every NPC knows.

The LLM only voices the character. It never sees facts the NPC shouldn't know, so it can't leak them.

Game mods are thin clients that report events and request dialog over a small HTTP API. Skyrim and Cyberpunk 2077 are the first targets.

## Status

| Piece | State |
|---|---|
| Design and research: prior art, save-state feasibility, monetization ([`docs/`](docs)) | Done |
| **Python PoC** ([`poc/`](poc)): engine, HTTP API, browser test page, ElevenLabs voice | **Done.** 19 offline tests; the live eval passes 30/30 with typical LLM latency of 2.4 s ([details](poc/README.md)) |
| **Cyberpunk 2077 mod** | **Planned.** See the [milestone](https://github.com/thoraxe/genpc-ai/milestone/1) and the [plan](.omc/plans/cyberpunk-mod-plan.md) |
| Skyrim SE/AE mod (SKSE) | Designed ([plan](.omc/plans/npc-engine-plan.md)), not started |

## Try the PoC
You need [uv](https://docs.astral.sh/uv/) and a `.env` file at the repo root with `ZAI_API_KEY` (any OpenAI-compatible LLM works, see [`poc/README.md`](poc/README.md)). `ELEVENLABS_API_KEY` is optional and adds voice.

```
uv run pytest -q                                         # offline tests
uv run uvicorn engine.api:app --app-dir poc --port 8000  # then open http://localhost:8000
```

The 8-step demo is in [`poc/README.md`](poc/README.md). Under each reply, the page shows exactly what was sent to the LLM.

## How it works
```
game mod ──events, clock, saves──▶ engine ──only this NPC's facts──▶ LLM
         ◀──line, 3 choices, voice──      ◀──JSON reply, validated──
```

**Rules** (all in `poc/engine/knowledge.py`):
- **Witnesses** get every fact.
- **Same town:** gossip arrives after half a day and keeps facts of importance 3 or higher.
- **Neighbouring town:** after 3 days, keeping importance 4 or higher.
- **Decay:** memory strength falls off exponentially with in-game days, slowed a little by recall.

**What the NPC learns from the player:** only facts that can be traced to what the player actually said.

## Layout
- `docs/`: research reports.
- `.omc/plans/`, `.omc/specs/`: the plans and the spec.
- `poc/`: the engine, the test UI, tests and scripts.

## Licence
Not chosen yet. The current leaning (see [`docs/monetization.md`](docs/monetization.md)) is AGPL plus a commercial licence, with Cyberpunk content free only.
