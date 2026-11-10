# World File

The world file describes one game world: its towns, places and NPCs. Each game gets its own world file. The engine reads it when it starts. The preset events file has events for tests and demos.

## Behavioral Rules

### The world file (`poc/data/world.json`)

1. The world file has these parts:
   - `setting`: the setting text. Every NPC gets it in the prompt. It tells the NPC how to speak.
   - `settlements`: the towns.
   - `locations`: the places. This part is optional.
   - `npcs`: the NPCs.
   - `rules`: the knowledge settings. This part is optional. See `knowledge.md` for each setting and its default.
2. If `setting` is empty, the prompt has no setting text.
3. Each town has an `id`, a `name`, and a list of next towns (`adjacent`).
4. Gossip goes only from a town to the towns in its own `adjacent` list. List the neighbour in both towns if you want gossip to go both ways.
5. Each place has an `id`, a `name`, and the town it belongs to (`near_settlement`).
6. Each NPC has an `id`, a `name`, a job (`role`), a town (`settlement`) and a description (`bio`).
7. An NPC can have a `voice_id` for the voice service. Without it, the NPC has no voice.
8. The engine does not contain any town, place or NPC. They all come from the world file.

### The preset events file (`poc/data/events.json`)

9. Each preset has a name, a `label` for the test page, a `type`, a `location`, `default_witnesses` and `facts`.
10. Each fact has a `text` and an `importance` from 1 to 5.

### The world now

11. The world file now describes a small fantasy world with 3 towns:
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

## Constraints

- Put everything about one game in its world file or its mod. Never in the engine code.

## Planned Changes

| Ticket | Summary |
|---|---|
| #7 | A world file for Cyberpunk 2077. Its districts are towns: Watson, Westbrook, City Center, Heywood, Santo Domingo, Pacifica, Dogtown and the Badlands. It has a starter cast. |
| #8 | NPCs that a mod adds while the game runs, not only NPCs from the world file. |
