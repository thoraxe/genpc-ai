# Dialog Pipeline

This file covers `what/conversation.md` and the voice rules in `what/http-api.md` (rules 27–30).

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `poc/engine/dialog.py` | `DialogEngine._turn` | The full turn. `open` and `choose` only call it. |
| `poc/engine/dialog.py` | `build_system_prompt`, `_knowledge_block`, `SOURCE_FRAMING` | The system prompt. Facts go to the LLM only here. |
| `poc/engine/dialog.py` | `DialogResponse`, `RememberItem` | Checks the LLM JSON. `three_choices` removes blanks, needs 3 or more, keeps 3. |
| `poc/engine/dialog.py` | `_history_messages`, `GREETING` | History of this session as user and assistant messages. |
| `poc/engine/dialog.py` | `FALLBACK`, `TurnResult` | The fallback reply; the turn that the API returns. |
| `poc/engine/providers/llm.py` | `OpenAICompatLLM.complete_json` | `response_format=json_object`, `max_tokens=500`, `timeout=20`, `max_retries=0`, optional `reasoning_effort`. |
| `poc/engine/providers/tts.py` | `ElevenLabsTTS.stream` | `POST /v1/text-to-speech/{voice_id}/stream`, `mp3_44100_128`, yields bytes. |

## Data Flow

`_turn(npc_id, session_id, player_text)` does these steps:
1. It gets `views` from `knowledge.retrieve(store.memories(npc_id), store.day, rules)`.
2. It builds the prompt with `build_system_prompt(npc, settlement name, views, day, rules, world.setting, crowd)`. `npc` comes from `Store.npc`, so an added NPC works the same way. For a crowd NPC, the prompt has no `remember` rule and a reply format without `remember`.
3. It gets the last 20 turns with `store.turns(npc_id)` and keeps those of this `session_id`. It adds the player text, or `GREETING` if there is none.
4. It tries a maximum of 2 times: `llm.complete_json`, then `json.loads`, then `DialogResponse.model_validate`.
   - On `JSONDecodeError` or `ValidationError`, it adds a "not valid JSON" user message and tries again.
   - On any other exception, it stops immediately.
5. If no reply is valid, it uses `FALLBACK` and sets `fallback=True`.
6. For a crowd NPC, it stores no fact and puts all `resp.remember` facts in `rejected` (`what/conversation.md` rule 22a). Else, if there is `player_text` and `resp.remember` is not empty, it checks the facts with `knowledge.conversation_memory`. The check uses all player lines of this session and the current text. It stores the kept facts with `store.add_memory`. It puts the other facts in `rejected`.
7. If it did not use the fallback, it finds `news_ids`. These are news views with a kept fact that is `grounded` in `resp.npc_line`. Then it calls `store.mark_used(views, news_ids)`.
8. It stores the turn with `store.add_turn`. On the first turn, the row id becomes the `session_id`, and `_turn` writes the body again.
9. It returns a `TurnResult`. The result includes `sent` (the system prompt and messages of the last try) and `raw_reply`.

## Key Abstractions

- **The knowledge-leak boundary** (`what/conversation.md` rules 6–9). `build_system_prompt` gets only these inputs:
  - `npc` and the settlement name;
  - the `views` that `retrieve` gave for that NPC;
  - the day, `rules` and the setting text.
- A gist view gives only its `kept_facts` and the text "You only vaguely remember the gist."
- Never give `world`, the memories of other NPCs, or `dropped_facts` to `build_system_prompt` (`REVIEW.md` §1).
- **Providers are Protocols.** Tests give a `FakeLLM` with `complete_json`. `/api/npc/{id}/prompt` uses `DialogEngine(store, None)`, because `preview_prompt` never calls the LLM.
- **The engine uses grounding two times.** `conversation_memory` uses it for player facts. `grounded(fact, npc_line)` uses it to find "told" news.

## Integration Points

| Consumer | Provider | Mechanism |
|---|---|---|
| `api.dialog_open` / `api.dialog_choose` | `DialogEngine.open` / `.choose` | `dialog()` makes a new `DialogEngine` for each request, with the shared `_llm` |
| `api.npc_prompt` | `DialogEngine.preview_prompt` | No LLM call |
| `api.audio` | `ElevenLabsTTS.stream` | `StreamingResponse`; gets the line from `store.turn(turn_id)` |
| `DialogEngine` | `LLMProvider.complete_json` | Protocol call |

## Implementation Notes

- The second try adds a message to `messages`. Thus `sent` shows the last try, with the correction message.
- `llm_ms` adds only the times of provider calls that returned (`total_ms or None`).
- The engine logs provider errors, cut to 200 characters. Never log keys.
- z.ai can send Chinese error text. A Windows console with cp1252 must not crash.
  - The scripts call `sys.stdout.reconfigure(encoding="utf-8")`.
  - The engine does not change stdout. It writes errors only through `log.warning`, and a `logging` handler reports an encoding error without a crash.
- The env settings have fallbacks:
  - `LLM_BASE_URL`, then `ZAI_BASE_URL`, then the z.ai coding URL.
  - `LLM_MODEL`, then `ZAI_MODEL`, then `glm-5.3-flash`.
- `api.session_start` gives the model name from env if the LLM does not exist yet.
- The engine does not cache TTS. Each `/api/audio/{turn_id}` call makes the audio again.
- A change to the prompt, retrieval or validation is high risk. Run the live eval and get a second, independent review (`CLAUDE.md`).
