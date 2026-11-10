# Knowledge Engine

This file covers `what/knowledge.md`, `what/saves-and-clock.md` and `what/world-file.md`.

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `poc/engine/knowledge.py` | `strength`, `view` | Decay formula and stage thresholds. |
| `poc/engine/knowledge.py` | `event_settlement`, `witness_memories`, `due_rumors` | Location → settlement; witness memories; hop1/hop2 memories. |
| `poc/engine/knowledge.py` | `retrieve` | Top-k views, with recent news first. |
| `poc/engine/knowledge.py` | `_STOP`, `_terms`, `grounded`, `conversation_memory` | Key-term check for player facts and for "told" news. |
| `poc/engine/store.py` | `Store` | SQLite tables `meta` (clock), `events`, `memories`, `turns`, `saves`. |
| `poc/engine/models.py` | `Rules`, `Memory`, `MemoryView` | Settings, and stored and derived memory shapes. |

## Data Flow

**Decay** (`what/knowledge.md` rules 17–23)
- `strength` = `salience * exp(-decay_lambda * age) * (1 + min(recall_cap, recall_boost * recalls))`.
- `age` is `now - created_day`. It is never less than 0.
- `view` gives stage `forgotten` below `forget_threshold` and `gist` below `gist_threshold`. Else it gives `detailed`.

**Event report** (`what/saves-and-clock.md` rules 6–9)
1. `api.report_event` builds a `WorldEvent` with the current `store.day` and a new id.
2. `Store.report_event` returns `[]` if the id is already in `events`.
3. It inserts the event.
4. It adds the `witness_memories` for NPCs that do not know the event yet.
5. It calls `Store.propagate()` and commits.
6. It returns all the new memories.

**Clock advance** (`what/saves-and-clock.md` rules 1–5)
1. `Store.advance(days)` raises `ValueError` if `days` is negative.
2. It adds `days` to `meta.day`.
3. It calls `propagate()` and commits.

**Propagate** (`what/knowledge.md` rules 3–16)
- `propagate` calls `knowledge.due_rumors(event, world, day, _knowers(event.id))` for each stored event.
- `due_rumors` adds each new NPC to `already_known`. Thus a hop1 NPC does not also get hop2, and a witness never gets a hop memory.
- `due_rumors` sets `created_day` to `event.day + delay` (the arrival day). It does not use `now`.

**Retrieval** (`what/knowledge.md` rules 24–28)
1. `retrieve` calls `view()` for each memory and removes `forgotten` views.
2. It sorts the views by strength, the strongest first.
3. It takes a maximum of `news_slots` news views. A news view has an `event_id`, is not `mentioned`, and is younger than `news_window_days`.
4. It puts the news views first, then the other views.
5. It keeps the first `max(retrieval_k, len(news))` views.

**Recall and "told"** (`what/conversation.md` rules 24–26)
- After a turn without the fallback line, `DialogEngine._turn` calls `Store.mark_used(views, news_ids)`.
- `mark_used` adds 1 to `recalls` for each retrieved memory.
- `mark_used` sets `mentioned = True` for each id in `news_ids`. `news_ids` holds the news memories with a kept fact that is `grounded` in the NPC line.

**One world at a time** (`what/world-file.md` rules 15–16s)
1. At import, `api.py` loads the test world (`poc/data/world.json`, `id` = `test`) into `store`, using `POC_DB`.
2. `POST /api/world` (`api.set_world`) validates the body with `WorldConfig` and `world_problems`. Every failure is `400`, never `422`.
3. Same `id` as the world in use: only `store.world` is replaced. The memories stay, and the new `rules` and `adjacent` lists apply from now on.
4. Different `id`: the old connection is closed, and a new `Store` opens `_db_path(id)`. A new file starts at `_start_day(world)`.
5. `_db_path` hashes the `id` into the file name, so a mod's `id` never becomes a path. Each world thus has its own clock, events, memories, turns and saves.
6. `presets` is `{}` in a mod world. The preset form then answers `404`.

**Save, load and reset** (`what/saves-and-clock.md` rules 10–17)
- `Store.save` writes every row of `STATE_TABLES` (`meta`, `events`, `memories`, `turns`) as JSON into `saves.blob`.
- `Store.load` deletes the rows of those tables. Then it inserts the saved rows again, with their old ids.
- `Store.reset` deletes the rows of the same tables and sets `meta.day` to the start day.
- No snapshot contains the `saves` table.

## Key Abstractions

- **`Memory` and `MemoryView`.** The engine stores `Memory`. It calculates `MemoryView` for a given day and never stores it. Thus decay changes nothing in the database. Only new hop memories add rows.
- **The engine never stores hop losses.** A hop memory holds only the facts above the hop threshold. `api.npc_knowledge` finds the "lost in retelling" facts. It compares the memory with the facts of its event. Gist losses are in `MemoryView.dropped_facts`.
- **One memory for each NPC and event.** `_knowers` enforces this in `report_event` and in `propagate`. No database constraint enforces it.
- **The memory body is JSON.** `memories.body` holds the full `Memory` without `id`. The `npc_id` and `event_id` columns are copies, for queries.

## Integration Points

| Consumer | Provider | Mechanism |
|---|---|---|
| `dialog.DialogEngine` | `knowledge.retrieve`, `knowledge.conversation_memory`, `knowledge.grounded` | Direct calls |
| `dialog.DialogEngine` | `Store.memories`, `Store.add_memory`, `Store.mark_used`, `Store.turns`, `Store.add_turn` | Direct calls |
| `api` routes | `Store.*`, `knowledge.view` | Direct calls under `api.lock` |
| World file | `Rules` | `WorldConfig.rules` default; the JSON can change it |

## Implementation Notes

- `knowledge.py` uses no LLM, no randomness and no wall clock. `Store.save` uses `time.time()` only for the `created` field of a save. That field is not part of the knowledge model.
- Adjacency goes in one direction. `due_rumors` reads only the `adjacent` list of the event's own settlement.
- `report_event` uses the event id to ignore a second report. The API makes a new id from the event count each time. Thus two API posts make two events.
- If you add stored state, add its table to `STATE_TABLES`. If you do not, a load does not remove that data. Data from after the save then stays in the game (`REVIEW.md` §3).
- The `turns` table keeps `session_id` in the JSON body. The row id of the first turn becomes the `session_id`. `_turn` writes it back with an `UPDATE`.
- `set_world` replaces the module globals `world`, `store` and `presets` under `api.lock`. Code that holds an old `Store` object (scripts, tests) keeps the old world.
- The store has one connection with `check_same_thread=False`. Only `api.lock` makes it thread-safe. Scripts and tests that use `Store` directly do not take the lock.
