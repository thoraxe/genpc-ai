# Deep Interview Spec: Game-Agnostic GenAI NPC Engine (Skyrim-first prototype)

## Metadata
- Interview ID: genpc-7f3a2c1e
- Rounds: 8 (+ Round 0 topology)
- Final Ambiguity Score: 18.6%
- Type: greenfield
- Generated: 2026-11-07
- Threshold: 0.2
- Threshold Source: default
- Initial Context Summarized: no
- Status: PASSED — pending approval

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.85 | 0.40 | 0.340 |
| Constraint Clarity | 0.78 | 0.30 | 0.234 |
| Success Criteria | 0.80 | 0.30 | 0.240 |
| **Total Clarity** | | | **0.814** |
| **Ambiguity** | | | **0.186** |

## Topology
| Component | Status | Description | Coverage Note |
|-----------|--------|-------------|---------------|
| NPC State Store | active | Personality, knowledge, conversation history, decaying memory, event/rumor propagation | AC-A, AC-B, AC-C |
| Mod-facing API | active | Game-agnostic protocol mods use to push events/state and request dialog | AC-A, AC-D, AC-F |
| Provider Adapter Layer | active | Pluggable LLM + TTS backends | AC-D, AC-E, AC-G |
| First Game Plugin (Skyrim SE/AE) | active | Thin custom SKSE/Papyrus mod speaking the engine API | AC-A..E |
| Prior-Art & Game-Selection Research | active | Survey existing systems; game selected (Skyrim) | AC-H |

## Goal
Build a **game-agnostic NPC engine** (the product) whose differentiator is the **knowledge model** — what each casual NPC knows, how world events spread to NPCs who didn't witness them, and how memories fade — exposed through a game-neutral API, backed by pluggable LLM/TTS providers, and proven end-to-end with a **thin custom Skyrim SE/AE mod** that renders generated dialog choices in a native-style dialog menu with voiced NPC replies.

## Constraints
- Engine core contains **no game-specific logic**; all game knowledge lives in game adapters (mods) and data packs.
- Real-time generation on **cloud LLMs** for v1 (pre-generation and local models are later options; adapter interface must not preclude them).
- Player input v1: **generated choices** (3–4 options) in a dialog menu; typed free input optional/later; no speech input in v1.
- Knowledge propagation v1: **hybrid** — the mod reports events + witnesses (the game knows line-of-sight); the backend handles second-hand spread with degraded detail. Simple propagation (location/proximity/time) in v1.
- Game time is supplied by the mod; memory decay and gossip timing use **in-game time**, not wall-clock.
- All thresholds (decay rates, gossip delays, latency budget) are **config**, not hard-coded.
- Skyrim side is a thin mod authored by us (not a fork/shim of Mantella/CHIM), speaking our own protocol. Existing mods may be read as reference for hooking techniques.
- Default stack (assumed, not interviewed — change in planning if desired): Python 3.12 + FastAPI, SQLite (with optional vector index for memory retrieval), HTTP/JSON on localhost between mod and engine.

## Non-Goals (v1)
- Key/quest-critical characters; quest generation or altering scripted quests.
- Full relationship/social graph published by the game (City-of-Gangsters-style) — **stretch goal**.
- Cyberpunk 2077 plugin — **stretch goal** (and the real proof of game-agnosticism).
- Speech-to-text player input; pre-generation; local LLMs.
- NPC actions (follow, attack, trade) driven by the LLM.
- Multiplayer, hosted/multi-tenant deployment.

## Acceptance Criteria
- [ ] **AC-A Event awareness/gossip:** Player clears a bandit camp near Riverwood. A Riverwood NPC who did **not** witness it references it (unprompted or in generated choices) within 1 in-game day. A Whiterun NPC later references a **vaguer** version.
- [ ] **AC-B Memory & decay:** NPC recalls a specific detail from a conversation 3 in-game days earlier; after ~30 in-game days it recalls only the gist, minor details gone.
- [ ] **AC-C Persistence:** All NPC state survives save/quit/reload (engine state keyed to save/playthrough ID).
- [ ] **AC-D Latency:** First NPC text appears ≤ ~3s after selecting a dialog option, using a cloud LLM.
- [ ] **AC-E Voice:** NPC reply is played in-game via one TTS provider with a per-NPC voice profile.
- [ ] **AC-F API is game-neutral:** The same API calls are exercisable from a non-Skyrim test client (CLI/simulator) reproducing AC-A and AC-B without the game running.
- [ ] **AC-G Pluggable providers:** Switching LLM provider (e.g. Anthropic ↔ OpenAI-compatible/OpenRouter) is a config change only; TTS has a defined interface with one implementation.
- [ ] **AC-H Prior-art note:** A short written comparison vs Mantella, CHIM/Herika and commercial platforms (Inworld, Convai, etc.), verified against current versions, stating what is reused as reference and what is differentiated.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| Build everything from scratch | Mantella/CHIM already solve Skyrim↔LLM plumbing | Own engine; differentiation = knowledge model + game-agnostic core |
| Dialog must be real-time | Pre-gen could hide latency (contrarian) | Real-time cloud for v1; pre-gen later |
| Player types/speaks | Native-feeling choices may be better | Generated choice menu; typing optional |
| Mod decides who knows what | Backend could simulate spread | Hybrid: mod reports witnesses, backend spreads gossip |
| Need custom Skyrim mod | Could reuse existing game side (simplifier) | Thin custom mod; own protocol |
| Voice is v1 | Not in original pass bar | Yes: LLM + one TTS in v1 |

## Technical Context
**Prior art (from model knowledge — verify in research task):**
- **Mantella** (Skyrim/Fallout 4): Python server + game mod; STT (Whisper) → LLM (OpenAI-compatible / OpenRouter) → TTS (xVASynth, XTTS, Piper) with lip files; NPC bios from data files; per-NPC conversation summaries. Free-form chat; no event-propagation/gossip model.
- **CHIM (formerly Herika)**: Skyrim; separate server with DB; logs nearby game events into NPC context; AI follower/NPC actions. Closest to the "witness" half of the hybrid.
- **Commercial**: Inworld AI, Convai, Nvidia ACE — character engines with memory/knowledge, SDK-focused (Unity/Unreal), not modding-focused.
- **Research**: "Generative Agents" (Park et al., 2023) — memory stream, recency/importance/relevance retrieval, reflection; good basis for decay + consolidation.

**Engine sketch:**
- `WorldEvent{id, type, location, time, actors, witnesses, salience, facts[]}` → witnesses get first-hand `Memory`; propagation job creates `Rumor` memories for NPCs by location/proximity after a delay with facts dropped/blurred per hop.
- Memory strength ≈ `salience × exp(-λ·Δgame_days)` boosted on recall; periodic consolidation compresses old detailed memories into gist summaries (LLM), then prunes details below threshold.
- Dialog request: mod sends `{npc_id, player_state, location, game_time}` → engine retrieves personality + top-k memories/rumors → LLM returns NPC line + 3–4 player choices (structured output) → TTS → mod displays/plays.
- Skyrim mod: SKSE/Papyrus; event hooks (combat/kill/location cleared), dialog trigger on NPC activation, choice menu via a dialogue-menu framework, HTTP via an SKSE HTTP plugin; voice playback requires generated audio + lip data placed where the engine can play it (technique to be confirmed from Mantella's approach).

**Biggest risks:** Skyrim audio/lip-sync injection; Skyrim version churn (SE vs AE / SKSE address libraries); 3s latency with LLM + TTS chained (stream text first, audio second).

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| NPC | core domain | id, game_ref, name, location, faction | has Personality, VoiceProfile, many Memories |
| Personality | core domain | traits, speech style, bio, values | belongs to NPC |
| Memory | core domain | content, facts, strength, salience, source(first-hand/rumor), game_time | belongs to NPC; may reference WorldEvent/Conversation |
| Conversation | core domain | turns, game_time, summary | NPC ↔ Player; produces Memories |
| WorldEvent | core domain | type, location, time, actors, witnesses, facts | reported by GamePlugin; spawns Memories/Rumors |
| Rumor (GossipRumor) | core domain | event_ref, fidelity, hop_count | derived from WorldEvent; becomes NPC Memory |
| Witness | supporting | npc_id, event_id | links NPC to WorldEvent |
| KnowledgePropagation | supporting | rules, delays, decay per hop | creates Rumors |
| RelationshipGraph | supporting (stretch) | edges, weights | drives propagation |
| DialogChoice | supporting | text, intent | generated per dialog turn |
| Player | core domain | id, reputation facts | participates in Conversations |
| GamePlugin / GameAdapter | external system | game, protocol version | calls Mod API |
| Provider (LLM/TTS) | external system | type, config | used by engine |
| VoiceProfile | supporting | provider, voice_id, params | belongs to NPC |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 6 | 6 | - | - | - |
| 2 | 9 | 3 | 0 | 6 | 67% |
| 3 | 11 | 2 | 0 | 9 | 82% |
| 4 | 11 | 0 | 0 | 11 | 100% |
| 5 | 12 | 1 | 0 | 11 | 92% |
| 6 | 12 | 0 | 0 | 12 | 100% |
| 7 | 13 | 1 | 0 | 12 | 92% |
| 8 | 14 | 1 | 0 | 13 | 93% |

## Interview Transcript
<details>
<summary>Full Q&A (8 rounds + topology)</summary>

**R0 Topology:** 5 components (State Store, Mod API, Provider Adapters, First Game Plugin, Prior-Art Research) → Looks right.
**R1 Purpose:** → Own engine, game-agnostic; existing tools are reference. (77%)
**R2 Demo bar:** → Talk to NPC, do something changing world state, NPC later aware of event/special info; native dialog menu with generated choices; typing optional. (55%)
**R3 Knowledge:** → Hybrid via relationship graph (City of Gangsters-like), mod publishes graph — stretch goal. (48%)
**R4 Latency (contrarian):** → Realtime, cloud to start; pregen etc. later. (43%)
**R5 Game:** → Skyrim first, Cyberpunk stretch. (36%)
**R6 Skyrim side (simplifier):** → Thin custom mod; asked how this differs from Mantella → answered (knowledge model + game-agnostic core). (32%)
**R7 Pass bar:** → A–D as written. (22.5%)
**R8 Providers:** → LLM + one TTS. (18.6%)
</details>
