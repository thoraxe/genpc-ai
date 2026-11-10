# Dialog Pipeline

Covers `what/conversation.md` and the voice rules in `what/http-api.md`.

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `poc/engine/dialog.py` | `DialogEngine._turn` | The whole turn. `open` and `choose` are thin wrappers. |
| `poc/engine/dialog.py` | `build_system_prompt`, `_knowledge_block`, `SOURCE_FRAMING` | The system prompt. The only place facts enter LLM input. |
| `poc/engine/dialog.py` | `DialogResponse`, `RememberItem` | Validation of LLM JSON. `three_choices` strips blanks, requires ≥3, truncates to 3. |
| `poc/engine/dialog.py` | `_history_messages`, `GREETING` | Same-session history as alternating user/assistant messages. |
| `poc/engine/dialog.py` | `FALLBACK`, `TurnResult` | Fallback reply; the turn response returned by the API. |
| `poc/engine/providers/llm.py` | `OpenAICompatLLM.complete_json` | `response_format=json_object`, `max_tokens=500`, `timeout=20`, `max_retries=0`, optional `reasoning_effort`. |
| `poc/engine/providers/tts.py` | `ElevenLabsTTS.stream` | `POST /v1/text-to-speech/{voice_id}/stream`, `mp3_44100_128`, yields bytes. |

## Data Flow

`_turn(npc_id, session_id, player_text)`:
1. `knowledge.retrieve(store.memories(npc_id), store.day, rules)` → `views`.
2. `build_system_prompt(npc, settlement name, views, day, rules, world.setting)`.
3. History: `store.turns(npc_id)` (last 20) filtered to `session_id`; append the player text or `GREETING`.
4. Up to 2 attempts: `llm.complete_json` → `json.loads` → `DialogResponse.model_validate`. On `JSONDecodeError`/`ValidationError`, append a "not valid JSON" user message and retry. On any other exception, break immediately.
5. No valid response → `FALLBACK`, `fallback=True`.
6. If `player_text` and `resp.remember`: ground against all player lines of this session plus the current text → `knowledge.conversation_memory` → `store.add_memory`. Unkept items go to `rejected`.
7. If not fallback: compute `news_ids` (news views whose kept facts are `grounded` in `resp.npc_line`) → `store.mark_used(views, news_ids)`.
8. `store.add_turn`; on the first turn, the row id becomes `session_id` and the body is rewritten.
9. Return `TurnResult` including `sent` (system + messages of the last attempt) and `raw_reply`.

## Key Abstractions

- **Knowledge-leak boundary:** `build_system_prompt` receives only `npc`, the settlement name, `views` from `retrieve` for that NPC, the day, rules and the setting text. Gist views contribute only `kept_facts` plus "You only vaguely remember the gist." Never pass `world`, other NPCs' memories, or `dropped_facts` into it (REVIEW.md §1).
- **Providers are Protocols.** Tests pass a `FakeLLM` with `complete_json`; `DialogEngine(store, None)` is used by `/api/npc/{id}/prompt` because `preview_prompt` never calls the LLM.
- **Grounding is reused twice:** for player facts (`conversation_memory`) and for news "told" detection (`grounded(fact, npc_line)`).

## Integration Points

| Consumer | Provider | Mechanism |
|---|---|---|
| `api.dialog_open` / `api.dialog_choose` | `DialogEngine.open` / `.choose` | `dialog()` builds a new `DialogEngine` per request with the lazily created `_llm` |
| `api.npc_prompt` | `DialogEngine.preview_prompt` | No LLM |
| `api.audio` | `ElevenLabsTTS.stream` | `StreamingResponse`; reads the line from `store.turn(turn_id)` |
| `DialogEngine` | `LLMProvider.complete_json` | Protocol call |

## Implementation Notes

- **Retry message:** the retry appends to `messages`; `sent` reflects the last attempt, including the correction message.
- **`llm_ms`** sums only successful provider calls (`total_ms or None`).
- **Logging:** provider errors are logged truncated to 200 chars. Do not log keys. z.ai may return Chinese error text; consoles with cp1252 must not crash (scripts call `sys.stdout.reconfigure(encoding="utf-8")`).
- **Env fallbacks:** `LLM_BASE_URL` → `ZAI_BASE_URL` → z.ai coding URL; `LLM_MODEL` → `ZAI_MODEL` → `glm-5.3-flash`. `api.session_start` reports the model name from env if the LLM is not yet built.
- **The TTS stream is not cached.** Each `/api/audio/{turn_id}` call regenerates the audio.
- Changing the prompt, retrieval or validation is **high risk**: run the live eval and get a second independent review (`CLAUDE.md`).
