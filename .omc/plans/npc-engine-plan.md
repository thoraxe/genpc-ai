# Plan: Game-Agnostic GenAI NPC Engine — Skyrim-first Prototype

- Source spec: `.omc/specs/deep-interview-npc-genai-backend.md`
- Status: **PENDING APPROVAL** (iteration 3 — consensus reached: Architect APPROVE WITH CHANGES, Critic conditional approve; all required changes applied)
- Mode: RALPLAN-DR short

## Requirements Summary
Game-agnostic engine (Python service) owning NPC personality, memory (in-game-time decay + deterministic gist consolidation), world events, and rumor propagation; a game-neutral, capability-negotiated HTTP/JSON API; pluggable LLM (Anthropic + OpenAI-compatible) and one TTS (ElevenLabs); a thin custom Skyrim mod that reports events/witnesses, opens a generated-choice menu, shows text and plays voice. Acceptance criteria AC-A..AC-H from the spec, sharpened below.

## RALPLAN-DR Summary

### Principles
1. **The knowledge model is the product** — all *stored* NPC knowledge is produced by deterministic engine code. The LLM only *renders* knowledge into speech/choices at dialog time; it never writes memory, rumors, or gists directly. (Conversation fact extraction uses the LLM as a *proposer* whose output is schema-validated and grounded in the transcript before the engine stores it — see 1.5.)
2. **Game-agnostic by construction** — engine never branches on game concepts. Event types and game refs are opaque strings; client differences are expressed through a capability handshake.
3. **Game constraints shape the protocol** — the Skyrim spikes gate the protocol freeze.
4. **Simulator is a first-class client** — everything provable without the game is proven in the simulator (AC-F).
5. **Thresholds are config with pinned, AC-satisfying defaults.**

### Decision Drivers
1. Highest uncertainty is Skyrim integration (transport, text-vs-audio timing, voice/lip, menu).
2. Differentiation lives in memory/propagation correctness — must be testable deterministically *and* validated against a real model.
3. AC-D latency measured end-to-end in game.

### Viable Options
**Option A' — Spike-gated engine-first (chosen).** Phase 0 spikes (≤1–2 weeks) run *first*; engine domain/knowledge-model work (no protocol) runs in parallel; the API protocol is frozen only after the capability sheet exists.
- Pros: knowledge model testable early; protocol shaped by real constraints; simulator satisfies AC-F.
- Cons: in-game demo comes late (Phase 3).

**Option B — Skyrim vertical slice first.**
- Pros: real constraints and an in-game demo from day one; strongest argument (Architect steelman): Papyrus can't stream, subtitles may be bound to voiced topics — these shape the API more than the engine does.
- Cons: knowledge model gets built last and under hard-coded Skyrim assumptions (violates P2); the real differentiator is under-tested.

**Option D — Walking skeleton (stub engine wired end-to-end in game in week 1, then deepen).**
- Pros: integration risk retired immediately; every later change is demo-able.
- Cons: largely equivalent to A' Phase 0 spikes but forces a throwaway protocol earlier; risk of the stub protocol ossifying.
- Why not chosen: A' Phase 0 spike S5 *is* a walking skeleton (event → stub engine → canned line + choices in game) but explicitly throwaway, preserving the protocol freeze until the capability sheet. A' therefore absorbs D's main benefit.

**Option C — Reuse Mantella/CHIM game side via shim** — *invalidated* by user decision (Round 6: own thin mod, own protocol). Reference reading only.

## Implementation Steps

### Phase 0 — Research & Skyrim spikes (sequential gate before protocol freeze)
Target runtime pinned now: **Skyrim AE (latest Steam) + SKSE64 matching + Address Library + CommonLibSSE-NG** (NG also supports SE 1.5.97; verify in 0.6).
- 0.1 `docs/prior-art.md`: verify Mantella, CHIM, Inworld, Convai, Nvidia ACE, Generative Agents — features, licenses, techniques referenced; license notes for any copied technique. (AC-H)
- 0.2 **S1 Transport**: Papyrus ↔ localhost HTTP via an SKSE plugin (survey which Mantella/CHIM use; else a small CommonLibSSE-NG plugin). Async request + callback event. Exit: JSON round-trip in game; **record: round-trip latency, whether chunked/polled partial responses are possible, JSON handling (plugin-side vs JContainers/PapyrusUtil)**.
- 0.3 **S2 Choice menu**: UIExtensions `UIListMenu` (SE/AE port) showing 3–4 dynamic strings, returning selection. Exit: index returned to Papyrus. Upgrade path (later): native DialogueMenu hook.
- 0.4 **S3 Voice + text timing**: play generated WAV on an NPC (candidate: loose voice file overwrite under `Data/Sound/Voice/<plugin>/<voicetype>/` for a placeholder topic, as Mantella reportedly does), with lip via FaceFXWrapper (user-installed CK assets; note licensing). Exit: NPC speaks arbitrary audio; **record: can text be shown before audio (subtitle widget/notification), lip-gen time, required audio format/sample rate, caching issues**.
- 0.5 **S4 Events/clock/witnesses**: detect kill / location-cleared; read `GameDaysPassed`; witnesses = actors within radius + `HasLOS` at event time, bounded (radius, max N actors). Exit: events logged with witnesses.
- 0.6 **S5 Throwaway walking skeleton**: stub HTTP server returns canned line + choices; mod shows them and plays a canned WAV. Exit: full in-game loop with no engine logic.
- 0.7 `docs/skyrim-capability-sheet.md`: pinned versions, results of S1–S5, latency measurements.
- **Go/No-Go gate G0:**
  - S1 fail → evaluate file-based IPC (mod writes request file, engine watches) before abandoning Skyrim; if both fail, switch game #1 (user decision).
  - S2 fail → fallback to MessageBox-based button menu (≤ 4 options) and request user sign-off on "native-style" wording.
  - S3 fail (audio) → AC-E downgraded to "audio without lip" or text-only — user decision. If text **cannot** precede audio, AC-D is re-baselined as "subtitle+audio start" budget (user sign-off).
  - S4 fail on witnesses → witnesses = actors in same cell/location (coarser, still meets AC-A).

### Phase 1 — Engine core + simulator (AC-A, AC-B, AC-C, AC-F)
Domain work (1.1–1.6) may begin during Phase 0; **1.7 protocol freeze requires G0**.
- 1.1 Scaffold: `engine/` (FastAPI, Python 3.12, uv), `engine/store/` (SQLite, SQLAlchemy, Alembic), `sim/` (CLI client + scenario runner), `packs/skyrim/` (NPC bios YAML, location graph, game_ref→npc_id map), `config/defaults.yaml`, `.env` (gitignored) for secrets. Import-lint: `engine` must not import `mods`/`packs`.
- 1.2 Domain: NPC, Personality, VoiceProfile, Player, Playthrough, Branch, EventLogEntry(seq, branch), WorldEvent(type: opaque tag, facts[{id, text, importance}], location, witnesses), Memory(source=first_hand|rumor|conversation, fact_ids[], detail_level=full|gist, salience, last_recalled), Rumor(event_id, hop, fidelity, fact_ids subset).
- 1.3 **Identity**: `game_ref` = opaque string; Skyrim adapter forms it as `<plugin>:<localFormID>` (load-order independent, ESL-safe). Unknown NPC on `dialog/open` → engine returns `{handled:false}` and mod falls back to vanilla dialog (v1; generic auto-persona is a later option, configurable).
- 1.4 **Save lineage (non-destructive)**: mod generates `playthrough_id` (UUID) on new game and persists `{playthrough_id, branch_id, last_event_seq}` in save (script properties). Engine keeps an append-only event tree per playthrough. On `session/start` with `(branch_id, last_event_seq)`: if seq is the branch head → continue; else fork a new branch from that seq and return the new `branch_id` for the mod to persist. All reads resolve state as of the branch ancestry. Nothing is deleted. Decay strength computed lazily from `(salience, last_recalled, now)`; rumor schedule derived per branch from the event log (deterministic).
- 1.5 **Memory creation**:
  - First-hand: witnesses get a memory of all event facts at event time.
  - Conversation: on `dialog/close`, LLM *proposes* facts `{text, importance 1–5}` from the transcript under a JSON schema; engine validates (schema, max N facts, each fact must cite turn indices present in transcript **and pass a grounding check: ≥ 60% content-word overlap with the cited turns**), then stores. Player statements are tagged `claimed_by_player`.
- 1.6 **Decay & gist (deterministic)**: `strength = salience · exp(-λ·Δdays) · (1 + recall_boost)`, with **Δdays measured from memory creation** (recalls only add boost; they do not reset the clock). When strength < `gist_threshold`, memory converts to `detail_level=gist` keeping only facts with importance ≥ `gist_min_importance`; below `forget_threshold` it's removed from retrieval (kept in log). LLM only phrases gists at render time.
- 1.7 **Propagation v1 (deterministic)**: event location resolves to a settlement via the pack's `near_settlement` mapping (e.g. the bandit camp → Riverwood); witnesses at t₀; same-settlement NPCs get rumor at t₀+d₁ (hop 1, drop facts with importance < 3); adjacent-hold NPCs at t₀+d₂ (hop 2, drop importance < 4). Computed lazily on clock advance, per branch. Catch-up after long waits processed in one pass; bound: ≤ 200 ms for 100 NPCs × 30 days in benchmark.
- 1.8 **Retrieval**: top-k by strength × relevance (tags/keywords) **plus a reserved "recent news" slot**: up to 2 rumors/first-hand events **received by this NPC** < 3 in-game days ago and not yet mentioned to this player, always included. "Mentioned" = the item was in the context of a dialog turn that was delivered to the player (deterministic, recorded per turn).
- 1.9 **API v1 (after G0)**: `POST session/start` (protocol_version, client capabilities: max_choices, choice_max_chars, supports_streaming, audio format, text_requires_audio; returns branch_id), `POST clock`, `POST events` (idempotency key required, deduplicated per `(branch_id, key)` so outbox replays after a fork land in the new branch), `PUT npcs/{game_ref}`, `POST dialog/open`, `POST dialog/choose`, `POST dialog/close`, `GET dialog/{id}/audio`, `GET debug/npcs/{id}/memories`. Responses shaped by negotiated capabilities.
- 1.10 Pinned defaults in `config/defaults.yaml` (chosen to satisfy ACs; tests assert them): `d₁ = 0.5 day`, `d₂ = 3 days`, `λ = 0.08/day`, salience first-hand/conversation = 1.0, rumor hop1 = 0.8, hop2 = 0.6; `recall_boost = 0.25 per recall, cap 0.5` (max factor ×1.5); `gist_threshold = 0.35`; `gist_min_importance = 3`; `forget_threshold = 0.05`. Check: no recall → day 3 = 0.79 (full), gist ≈ day 13, forgotten ≈ day 37; **worst case (max boost)** → gist ≈ day 18, day 30 = 0.14 (gist, margin 2.5×), forgotten ≈ day 42. AC-B tests run both the no-recall and max-recall cases.
- **Phase 1 exit**: all deterministic scenario tests green (below), import-lint green, catch-up benchmark within bound.

### Phase 2 — Providers & dialog orchestration (AC-D, AC-E, AC-G)
- 2.1 `engine/providers/llm/`: `LLMProvider` (plain-text streaming + JSON-schema call); adapters: Anthropic, OpenAI-compatible (OpenAI, OpenRouter, local). Provider/model chosen by config.
- 2.2 **Two-call dialog pipeline**: Call 1 streams `npc_line` as plain text (personality + retrieved memories + scene, "know only what's listed"). Call 2 (started as soon as Call 1 completes, overlapping TTS) generates 3–4 choices as schema JSON. No JSON streaming dependency → portable across providers. Fallback choices (generic: "Tell me more", "Any news?", "Goodbye") on parse failure / timeout. Use provider prompt caching for the shared prefix (personality + memories) across Call 1/Call 2.
- 2.3 `engine/providers/tts/`: `TTSProvider`; ElevenLabs adapter; per-NPC VoiceProfile; output converted to the format S3 established; lip generation via configured tool if available.
- 2.4 **Failure handling**: provider timeout (configurable, default 6s) or error → canned in-character line + fallback choices; engine logs incident. Rate limiting/backoff per provider.
- 2.5 **Cost & observability**: per-turn token counts and estimated cost logged; per-stage timings; `max_tokens` budget per call; daily cost cap config.
- 2.6 Secrets: API keys from env / `.env` only; redacted from logs.
- **Phase 2 exit**: AC-G and live-eval tier pass in simulator; latency report produced.

### Phase 3 — Skyrim thin mod (AC-A..E in game)
- 3.1 `mods/skyrim/`: event reporter with **outbox** (queued in script storage, retried with idempotency keys until acked), clock sync on load/sleep/wait/fast-travel, save-lineage token persistence, NPC activation → `dialog/open` (timeout 8s → vanilla dialog); `dialog/choose` timeout 8s mid-conversation → canned in-character line + single "Goodbye" choice, then exit, choice menu loop, text display, voice playback.
- 3.2 Skyrim pack: ~10 casual NPCs in Riverwood/Whiterun with bios, voice profiles, `game_ref`s; location adjacency.
- 3.3 `mods/skyrim/TESTPLAN.md` manual checklist for AC-A..E incl. save lineage round trip and engine-killed-mid-game.
- **Phase 3 exit**: TESTPLAN all pass on pinned runtime.

### Phase 4 — Stretch (not in v1 acceptance)
**Save-attached state (user priority #1 stretch; feasibility confirmed in `docs/save-state-feasibility.md`):** an SKSE plugin writes `META` + a compressed `SNAP` engine snapshot into the `.skse` co-save on `kSaveGame`/save callback, and the engine restores it on load. The co-save becomes the source of truth and the engine a cache keyed by `(lineage_id, save_seq)`. v1's lineage tree (1.4) stays as the fallback when the co-save is missing. Phase 0 should add a quick S6 spike: write and read a 1 MB co-save record and time the save/load. Relationship graph from mod; Cyberpunk 2077 adapter (CET/redscript) validates capability handshake; pre-generation; local LLM; native DialogueMenu hook; auto-personas for unknown NPCs.

**Key characters and content packs (future; see `docs/save-state-feasibility.md`):**
- Add an NPC `tier: casual|key` field. Key NPCs get:
  - a locked personality;
  - facts gated by quest stage, from a `TESQuestStageEvent` sink and rebuilt from quest stages on load;
  - a spoiler guard.
- Vanilla quest dialogue is never replaced.
- Third-party content packs:
  - add namespaced NPCs, events and stage-gated knowledge, and a policy for how much the LLM may generate;
  - connect as an optional dependency through native Papyrus functions and ModEvents;
  - each get their own section of the co-save, dropped when their ESP is removed;
  - can only add state, never overwrite it.
- Cyberpunk: read other mods' FactsDB facts.

**Second-game candidates:** Fallout 4 reuses the co-save design as-is, since F4SE has the same serialization interface. BG3, Bannerlord, RimWorld and Stardew store data inside the save. Starfield and Oblivion Remastered support only a side file or a token.

**Monetization constraints (see `docs/monetization.md`):**
- Decide before the first commit: AGPL-3.0 plus a commercial license, with a CLA.
- Keep the engine and hosted service free of game assets and game branding.
- Cyberpunk stays free only.
- Never host cloned voices of the game's actors.

## Acceptance Criteria → Verification
**Deterministic tier (pytest, fake LLM, CI):**
- AC-A: after camp-cleared event at t₀ with no Riverwood witnesses: at t₀+1 day the Riverwood NPC's dialog context contains the rumor in the recent-news slot; Whiterun NPC's rumor fact set ⊂ Riverwood's with lower fidelity at t₀+d₂; **negative**: a Solitude NPC's context has no event facts.
- AC-B: conversation fact F (importance 2) present at day 3 with `detail_level=full`; at day 30 F absent, gist memory present with only importance ≥ gist_min facts.
- AC-C: restart engine → state identical; save-lineage test: save A (day 10) → load older save (day 5) → play to day 12 → load A → A's history intact, day-12 branch facts absent.
- AC-F: above scenarios via simulator; import-lint green.
- Failure: provider error → canned line; duplicate `POST events` with same key → single event.

**Live tier (real model eval, `sim eval`, run per release):**
- AC-A: 10 dialog openings with the informed Riverwood NPC → ≥ 8/10 reference the event (LLM-judge with rubric + keyword check); uninformed Solitude NPC → 0/10 mention it.
- AC-A (Whiterun): 10 openings with the Whiterun NPC at t₀+3–5 days → ≥ 8/10 reference the event; judge confirms no detail outside the Riverwood fact set.
- AC-B: 10 runs day 3 → ≥ 8/10 recall detail F; day 30 → ≤ 1/10 state F specifically.
- AC-G: AC-A live eval passes on both an Anthropic model and an OpenAI-compatible model via OpenRouter (model IDs live in `config/eval.yaml`, verified at Phase 2 start), switched only via config.
- Judge: a configured LLM judge (preferably a different model than the generator) with rubrics in `sim/eval/rubrics/`, plus a keyword check; both must agree for a pass.
- Integration tests replay recorded provider responses (cassettes) to keep CI deterministic.

**In-game (TESTPLAN):**
- AC-D: end-to-end from choice selected → first NPC text visible ≤ 3.0 s p50 / ≤ 4.5 s p95 over 20 turns; audio start measured separately (target ≤ 6 s). If S3 showed text must ride audio, budget per G0 re-baseline.
- AC-E: ≥ 5 NPCs speak generated audio with distinct voices (lip-sync if S3 succeeded).
- AC-A/B/C manual scenarios on pinned runtime.
- AC-H: `docs/prior-art.md` with sources, dates, licenses.

## Risks and Mitigations
| Risk | Mitigation |
|---|---|
| No streaming/partial responses through Papyrus | S1 records it; two-call pipeline still returns full line fast; AC-D measured end-to-end |
| Text can't precede audio | S3 records; G0 re-baseline with user sign-off; shorter lines + fast TTS model |
| Voice/lip injection fragile | S3 first; G0 fallback ladder (no-lip → text-only) |
| UIListMenu doesn't read as "native-style" | G0 sign-off; DialogueMenu hook in Phase 4 |
| Skyrim runtime updates break SKSE plugins | Pin runtime in capability sheet; prefer Papyrus + established plugins |
| LLM hallucinates knowledge | Context only holds retrieved memories; live-tier negative check (0/10) |
| Missed events break gossip | Mod outbox + idempotency keys |
| Engine down mid-game | Mod timeouts → vanilla dialog; outbox retries |
| Save reloads corrupt state | Append-only event tree + lineage token; round-trip test |
| Cost overruns (e.g. consolidation after long waits) | Consolidation is deterministic (no LLM); per-call token budgets; daily cost cap |
| Load-order changes FormIDs | `<plugin>:<localFormID>` refs |

## Verification Steps
1. `pytest` (unit, deterministic scenarios, cassette integration) + import-lint.
2. `sim eval --live` live-tier report (pass rates, cost, latency).
3. `mods/skyrim/TESTPLAN.md` on pinned runtime, with in-game latency log.

## Open Questions (user sign-off at G0 if triggered)
- Is UIExtensions list menu acceptable as "native-style dialog menu" for v1?
- If Skyrim can't show text before audio, accept AC-D as "subtitle+audio ≤ ~4.5 s"?
- AC-D p95 ≤ 4.5 s loosens the spec's "~3 s" (p50 stays ≤ 3 s) — confirm.

## ADR
- **Decision:** Spike-gated engine-first (Option A'): Skyrim feasibility spikes S1–S5 and a throwaway walking skeleton run first; the knowledge model (deterministic memory, decay, gist, rumor propagation, save-lineage event tree) is built in parallel; the game-neutral, capability-negotiated API is frozen only after go/no-go gate G0.
- **Drivers:** Skyrim integration is the highest uncertainty; the differentiator (knowledge model) must be deterministic and testable; AC-D latency must hold end-to-end in game.
- **Alternatives considered:** B (Skyrim vertical slice first): rejected because it bakes Skyrim assumptions into the core. D (walking skeleton): absorbed as spike S5. C (reuse the Mantella/CHIM game side): invalidated by the user's decision.
- **Why chosen:** retires game risk before the protocol is frozen, while keeping the core game-agnostic and verifiable without the game or an LLM.
- **Consequences:** the in-game demo arrives in Phase 3; two-tier verification (deterministic + live eval) adds eval-harness work; the two-call LLM pipeline costs a second request (mitigated by prompt caching).
- **Follow-ups:** G0 user sign-offs (menu style, AC-D baseline); verify model IDs at Phase 2 start; Phase 4 stretch (relationship graph, Cyberpunk adapter as the agnosticism proof).

## Changelog
- Iter 2: save lineage tree (Architect 1, Critic 6); deterministic gist + LLM-proposer extraction with validation (A2, C4); two-call plain-text pipeline (A3); capability handshake, opaque tags/refs (A4, C5); protocol freeze gated on G0 + go/no-go fallbacks (A5, C9); AC-D split end-to-end (A6, C7); live eval tier + cassettes (A7, C1, C10); lip/licensing in S3 (A8); recent-news slot (C2); pinned defaults (C3); outbox/idempotency/timeouts (C8); phase exits (C9); Option D walking skeleton evaluated (C); secrets, cost, catch-up bound, pinned runtime (C optional).
- Iter 3: per-branch idempotency (A-N1); Δdays from creation, boost cap 0.5, worst-case decay check (A-N2, C3); gist_min_importance=3, rumor salience (A-N3); camp→settlement mapping (A-N4); model IDs moved to config (A-N5, C10); prompt caching (A-N6); recent-news slot counts from receipt + Whiterun live eval (C-N1); deterministic 'mentioned' (C-N2); judge spec + grounding check (C-N3); dialog/choose timeout (C8); AC-D p95 added to sign-offs (C7); ADR added.
