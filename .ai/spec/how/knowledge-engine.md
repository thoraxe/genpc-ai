# Knowledge Engine

Covers `what/knowledge.md`, `what/saves-and-clock.md` and `what/world-file.md`.

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `poc/engine/knowledge.py` | `strength`, `view` | Decay: `salience * exp(-decay_lambda * age) * (1 + min(recall_cap, recall_boost * recalls))`; stage thresholds. |
| `poc/engine/knowledge.py` | `event_settlement`, `witness_memories`, `due_rumors` | Map a location to its settlement; witness memories; hop1/hop2 rumor memories. |
| `poc/engine/knowledge.py` | `retrieve` | Top-k non-forgotten views plus guaranteed recent-news slots. |
| `poc/engine/knowledge.py` | `_STOP`, `_terms`, `grounded`, `conversation_memory` | Key-term grounding for player facts and for news "told" detection. |
| `poc/engine/store.py` | `Store` | SQLite tables `meta` (clock), `events`, `memories`, `turns`, `saves`. |
| `poc/engine/models.py` | `Rules`, `Memory`, `MemoryView` | Tunables and stored/derived memory shapes. |

## Data Flow

**Event report:** `api.report_event` → builds `WorldEvent` (id, current `store.day`) → `Store.report_event` → skip if id exists → insert event → `knowledge.witness_memories` (minus existing knowers) → `Store.propagate()` → commit. Returns the new memories.

**Clock advance:** `Store.advance(days)` → raises on negative → set `meta.day` → `propagate()` → commit.

**Propagate:** for every stored event, `knowledge.due_rumors(event, world, day, _knowers(event.id))`. `due_rumors` mutates `already_known` as it adds, so hop1 NPCs are not re-added as hop2, and a witness never gets a rumor. Memories are created with `created_day = event.day + delay` (arrival time), not `now`.

**Retrieval:** `knowledge.retrieve(memories, day, rules)` → `view()` each → drop forgotten → sort by strength desc → pick up to `news_slots` news views (has `event_id`, not `mentioned`, age < `news_window_days`) → news first, then the rest → slice to `max(retrieval_k, len(news))`.

**Recall / mentioned:** after a non-fallback turn, `DialogEngine._turn` calls `Store.mark_used(views, news_ids)`: every retrieved memory gets `recalls += 1`; news memories whose kept facts are `grounded` in the NPC line get `mentioned = True`.

**Save/load:** `Store.save` dumps every row of `STATE_TABLES` (`meta`, `events`, `memories`, `turns`) as JSON into `saves.blob`. `Store.load` deletes those tables and re-inserts the rows, including original ids. `reset` deletes the same tables and resets `meta.day`. The `saves` table is never part of a snapshot.

## Key Abstractions

- **`Memory` vs `MemoryView`:** `Memory` is stored. `MemoryView` is derived at a given day (strength, stage, kept/dropped facts) and is never stored. Decay is therefore lazy: nothing changes in the DB as time passes, except new rumor rows.
- **Rumor losses are never stored.** A hop memory only holds facts above the hop threshold. The inspector computes "lost in retelling" by diffing against the event's facts (`api.npc_knowledge`). Gist losses are `MemoryView.dropped_facts`.
- **One memory per (NPC, event).** Enforced via `_knowers` in both `report_event` and `propagate`, not by a DB constraint.
- **Memory body as JSON.** `memories.body` holds the whole `Memory` minus `id`; `npc_id` and `event_id` are duplicated into columns for querying.

## Integration Points

| Consumer | Provider | Mechanism |
|---|---|---|
| `dialog.DialogEngine` | `knowledge.retrieve`, `knowledge.conversation_memory`, `knowledge.grounded` | Direct calls |
| `dialog.DialogEngine` | `Store.memories`, `Store.add_memory`, `Store.mark_used`, `Store.turns`, `Store.add_turn` | Direct calls |
| `api` routes | `Store.*`, `knowledge.view` | Direct calls under `api.lock` |
| World file | `Rules` | `WorldConfig.rules` pydantic default, overridable in JSON |

## Implementation Notes

- **No LLM, randomness or wall-clock in `knowledge.py`.** `Store.save` uses `time.time()` only for the save's `created` field, which is outside the knowledge model.
- **Adjacency is one-directional.** `due_rumors` reads only the event settlement's own `adjacent` list.
- **`report_event` idempotency is by event id**, but the API builds a fresh id from the event count, so repeated API posts create new events.
- **Adding stored state?** Add the table to `STATE_TABLES`, or saves will silently keep the new data across a load (REVIEW.md §3).
- **The `turns` table** stores `session_id` inside the JSON body. The first turn's own row id becomes the session id, written back with an `UPDATE` in `_turn`.
- **Single connection, `check_same_thread=False`.** Thread safety comes only from `api.lock`. Scripts and tests that use `Store` directly do not take the lock.
