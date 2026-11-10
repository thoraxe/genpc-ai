# World File

The world file describes one game world: its towns, places and NPCs. Each game gets its own world file. The engine has one test world. A mod sends its own world to the engine. The preset events file has events for the tests.

## Behavioral Rules

### The parts of a world file

1. The world file has these parts:
   - `id`: the name of the world, for example `harbor_city`.
   - `start_day`: the day on the clock when the world starts. This part is optional. The default is `POC_START_DAY`.
   - `setting`: the setting text. Every NPC gets it in the prompt. It tells the NPC how to speak.
   - `settlements`: the towns.
   - `locations`: the places. This part is optional.
   - `npcs`: the NPCs.
   - `calendar`: how long a day is in the game. This part is optional. `[PLANNED: #9]`
   - `rules`: the knowledge settings. This part is optional. See `knowledge.md` for each setting and its default.
1a. `calendar` has `hours_per_day`: the number of hours in one day of the game. The default is `24`. `[PLANNED: #9]`
1b. `hours_per_day` must be more than 0. Else the world is not correct. `[PLANNED: #9]`
2. If `setting` is empty, the prompt has no setting text.
3. Each town has an `id`, a `name`, and a list of next towns (`adjacent`).
4. Gossip goes only from a town to the towns in its own `adjacent` list. List the neighbour in both towns if you want gossip to go both ways.
5. Each place has an `id`, a `name`, and the town it belongs to (`near_settlement`).
6. Each NPC has an `id`, a `name`, a job (`role`), a town (`settlement`) and a description (`bio`).
6a. The `id` of a world-file NPC can be the record ID of the character. Example: `npc.harbor_vendor`. `[PLANNED: #8]`
6b. If the `id` is the record ID, the mod can find the world-file NPC. `[PLANNED: #8]`
7. An NPC can have a `voice_id` for the voice service. Without it, the NPC has no voice.
7a. The world file can have a voice list (`voice_pool`). It has a list for `female` and a list for `male`. `[PLANNED: #8]`
7b. The engine chooses a voice from the voice list by the NPC's ID. The same NPC always gets the same voice. `[PLANNED: #8]`
7c. If the mod sends no gender, the engine chooses from all voices in the voice list. `[PLANNED: #8]`
7d. If the voice list is empty or not in the world file, added NPCs have no voice. `[PLANNED: #8]`
7e. The world file can have a general description (`generic_bio`). Each added NPC gets it. `[PLANNED: #8]` (owner question 5)
7f. If the world file has no general description, the engine uses "You are an ordinary person. You have no special story." `[PLANNED: #8]` (owner question 5)
8. The engine does not contain any town, place or NPC. They come from the world file or from the mod (`http-api.md` rule 31). `[PLANNED: #8]`

### The preset events file (`poc/data/events.json`)

9. Each preset has a name, a `label` for the test page, a `type`, a `location`, `default_witnesses` and `facts`.
10. Each fact has a `text` and an `importance` from 1 to 5.

### The test world

11. The test world (`poc/data/world.json`, `id` = `test`) is a small fantasy world with 3 towns:
   - Riverwood, next to Whiterun;
   - Whiterun, next to Riverwood;
   - Solitude, with no next towns.
12. It has one place: Embershard Mine, which belongs to Riverwood.
13. It has 4 NPCs: Hrolf (miner, Riverwood), Torvald (innkeeper, Riverwood), Eirik (town guard, Whiterun) and Sabine (cloth merchant, Solitude).
14. It has 2 presets: "Clear the bandits at Embershard Mine" (witness: Hrolf) and "Kill a wolf at the Riverwood gate" (witness: Torvald).

Examples:
- If you add `"rules": {"hop1_delay_days": 1.0}` to the world file, then same-town gossip arrives after 1 day.
- If Riverwood lists Whiterun but Whiterun does not list Riverwood, then gossip goes from Riverwood to Whiterun only.
- If you change `setting`, then every NPC speaks in the new style. No code changes.

### Which world the engine uses

15. When the engine starts, it uses the test world. The test page and the tests use it.
16. A mod sends its own world to the engine with `POST /api/world`.
16a. Send the world after `POST /api/session/start`, and before any event or conversation.
16b. The engine uses one world at a time: the last world that a mod sent.
16c. A mod cannot use the world name `test`.
16d. Each world has its own clock, events, memories, turns, added NPCs and saves.
16e. A switch to a different world switches all of these. A reset or a load changes only the world in use.
16f. Nothing from one world goes into a different world. This is true for prompts, gossip, the inspector and saves.
16g. A new world starts at its start day. Example: a world with `start_day` = `0` starts at day 0.
16h. A reset sets the clock of the world in use to its start day.
16i. A mod can send a world `id` that the engine has knowledge for. Then the engine uses that knowledge again.
16j. A world can change between two sends, for example after a mod update. The engine uses the new world. The memories stay. (owner question 1)
16k. After such a change: (owner question 1)
   - An NPC that is not in the new world is unknown. Its memories stay, but requests for it get `404`.
   - New next towns apply to gossip that has not arrived yet.
   - New knowledge settings apply to all memories from then on.
   - A new day length applies to the next `hours` from the mod. The clock and the memories keep their days. `[PLANNED: #9]` (owner question 4)
16l. Do not use an NPC `id` again for a different character. The new character gets the memories of the old one.
16m. If the world is not correct, the engine refuses it. It keeps the world in use, and the answer tells why.
16n. A world is not correct if one of these is true:
   - It has no `id`, no `settlements` or no `npcs`.
   - Two towns, two places or two NPCs have the same `id`.
   - An `adjacent` list, a place or an NPC names a town that is not in the world.
   - `hours_per_day` is 0 or less. `[PLANNED: #9]`
16o. After a switch, a request for an NPC of a different world gets `404`.
16p. Conversation, turn and save numbers belong to one world. Do not use them in a different world.
16q. The engine does not keep the mod's world after it stops. After a restart, it uses the test world again.
16r. `POST /api/session/start` and `GET /api/world` give the `id` of the world in use. If it is not the mod's world, send the world again.
16s. Presets belong only to the test world. In a mod world, `GET /api/world` gives no presets.

Examples (`harbor_city` is a made-up mod world with `start_day` = `0`):
- The engine starts with the test world. A mod sends `harbor_city`. Then `harbor_city` is the world at day 0. A request to talk to Torvald gets `404`.
- The player plays until day 12, then closes the game. The next day, the mod sends `harbor_city` again. Then the clock is at day 12, and every NPC remembers what it knew.
- The engine restarts while the game runs. `POST /api/session/start` gives `test`. The mod sends `harbor_city` again and continues.
- A mod update removes the NPC `dockworker_1`. A request to talk to it gets `404`. If a later update adds it again, it still has its memories.

## Constraints

- Put everything about one game in its world file or its mod. Never in the engine code.

## Planned Changes

| Ticket | Summary |
|---|---|
| #7 | A mod sends its own world to the engine. The first mod's world is in the mod's specs. |
| #8 | NPCs that a mod adds while the game runs, not only NPCs from the world file. |
