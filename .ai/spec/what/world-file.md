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

### Which world the engine uses

15. When the engine starts, it uses the test world (`poc/data/world.json`). The test page and the tests use it. `[PLANNED: #7]`
16. A mod sends its own world to the engine with `POST /api/world`. Send it before any event or conversation. `[PLANNED: #7]`
16a. The engine uses one world at a time: the last world that a mod sent. `[PLANNED: #7]`
16b. Each world has a name (`id`), for example `cyberpunk`. `[PLANNED: #7]`
16c. Each world keeps its own knowledge. Events, memories, turns and saves of one world never appear in a different world. `[PLANNED: #7]`
16d. A mod can send a world that the engine knew before. Then the engine uses the knowledge that it kept for that world. `[PLANNED: #7]`
16e. If the world that the mod sends has changes, for example a new NPC, the engine uses the new world. The memories stay. `[PLANNED: #7]` (owner question 7)
16f. If the world is not correct, the engine refuses it and keeps the old world. The answer tells why. `[PLANNED: #7]`
16g. The engine does not keep the mod's world after it stops. The mod sends the world at each game start. `[PLANNED: #7]`

Example: the engine starts with the test world. The Cyberpunk mod sends `cyberpunk`. Then Night City is the world, and Torvald does not exist.

### The Cyberpunk world

17. The Cyberpunk world file is `mods/cyberpunk/world.json`. The mod ships it. `[PLANNED: #7]`
17a. The Cyberpunk world has 7 towns. Each town is a district of Night City. `[PLANNED: #7]`
18. Each town lists its next towns in this table. Each link is in both towns. `[PLANNED: #7]` (owner question 3)

| Town (`id`) | Next towns |
|---|---|
| Watson (`watson`) | City Center, Westbrook |
| Westbrook (`westbrook`) | Watson, City Center, Badlands |
| City Center (`city_center`) | Watson, Westbrook, Heywood, Santo Domingo |
| Heywood (`heywood`) | City Center, Santo Domingo, Pacifica |
| Santo Domingo (`santo_domingo`) | City Center, Heywood, Pacifica, Badlands |
| Pacifica (`pacifica`) | Heywood, Santo Domingo |
| Badlands (`badlands`) | Westbrook, Santo Domingo |

19. The Cyberpunk world file has no Dogtown. An event in Dogtown goes only to its witnesses (`knowledge.md` rule 5a). `[PLANNED: #7]` (owner question 2)
20. Each part of a district is a place. It belongs to its district. `[PLANNED: #7]` (owner question 6)

| Place (`id`) | Town |
|---|---|
| Little China (`little_china`), Kabuki (`kabuki`), Northside (`northside`), Arasaka Waterfront (`arasaka_waterfront`) | Watson |
| Japantown (`japantown`), Charter Hill (`charter_hill`), North Oak (`north_oak`) | Westbrook |
| Corpo Plaza (`corpo_plaza`), Downtown (`downtown`) | City Center |
| The Glen (`the_glen`), Wellsprings (`wellsprings`), Vista del Rey (`vista_del_rey`) | Heywood |
| Arroyo (`arroyo`), Rancho Coronado (`rancho_coronado`) | Santo Domingo |
| Coastview (`coastview`), West Wind Estate (`west_wind_estate`) | Pacifica |

Example: an event in Kabuki counts as an event in Watson. Gossip goes to City Center and Westbrook.

21. The starter cast has these 9 NPCs. `[PLANNED: #7]` (owner question 1)

| NPC | Job (`role`) | Town | Description (`bio`) | Check |
|---|---|---|---|---|
| Regina Jones | fixer | Watson | A calm, careful fixer who gives gigs in Watson. She cares about the people of her district more than about money. | Exists. Confirm that the player can talk to her in person. |
| Robert Wilson | gun shop owner | Watson (Little China) | An old soldier who runs a small gun shop and shooting range. He is friendly and gives honest advice about guns. | Exists. |
| Cassius Ryder | ripperdoc (cyberware doctor) | Watson (Little China) | A tired street doctor who installs cyberware. He talks little and wants payment first. | To confirm: name and place. |
| Wakako Okada | fixer | Westbrook (Japantown) | An old, sharp fixer with strong links to the Tyger Claws. She is polite, but she does not forgive a broken deal. | Exists. |
| Dino Dinovic | fixer | City Center | A smooth fixer who works for clients in the corporate towers. He talks about business and money. | Exists. Confirm that the player can talk to him in person. |
| Sebastian "Padre" Ibarra | fixer | Heywood | An older fixer with ties to the Valentinos. He speaks quietly and values loyalty and family. | Exists. Confirm the place. |
| Muamar "El Capitan" Reyes | fixer | Santo Domingo | A loud, cheerful fixer who also sells cars. He likes to tell jokes about his deals. | To confirm: town. |
| Mr. Hands | fixer | Pacifica | A polite, mysterious fixer who dresses well. He speaks with old-fashioned manners. | Exists. Phantom Liberty uses him a lot. Confirm that he is OK. |
| Dakota Smith | fixer | Badlands (Rocky Ridge) | A practical fixer who runs a garage in the desert. She speaks plainly and trusts actions more than words. | Exists. |

22. Each Cyberpunk NPC `id` will be the game's record ID: the fixed name of the character in the game data. The mod uses this ID to find the NPC. We must still confirm the IDs in the game. `[PLANNED: #7]`
23. Each NPC in the starter cast has no `voice_id` now. The owner will choose the voices later (#1). `[PLANNED: #7]`
24. The Cyberpunk setting text is this: `[PLANNED: #7]`

> Speak like a person who lives in Night City in the year 2077. Night City is a hard, dangerous city. Corporations and gangs control it. Use some street words, but keep your meaning clear.

25. In the Cyberpunk world file, next-town gossip arrives after 1 day (`hop2_delay_days` = `1.0`). Example: event on day 41, gossip on day 42. `[PLANNED: #7]` (owner question 4)
26. The Cyberpunk world file does not change the other knowledge settings. `[PLANNED: #7]`

### The Cyberpunk presets (`mods/cyberpunk/events.json`)

27. The Cyberpunk preset file has 3 presets. Only the tests use it. `[PLANNED: #7]`

**Preset 1:** "Clear a Maelstrom gig in Northside". Place: Northside (Watson). Witness: Regina Jones.

| Fact | Importance |
|---|---|
| The Maelstrom hideout in Northside is gone | 5 |
| A solo merc did it alone | 4 |
| The merc took a crate of military weapons | 3 |
| The merc used a silenced pistol | 2 |
| It happened after midnight | 1 |

**Preset 2:** "Fight the police in The Glen". Place: The Glen (Heywood). Witness: Padre.

| Fact | Importance |
|---|---|
| A merc fought the police in The Glen | 5 |
| Two police officers died | 4 |
| The merc escaped in a stolen car | 3 |
| The car was yellow | 1 |

**Preset 3:** "Clear a Wraiths camp in the Badlands". Town: Badlands. Witness: Dakota Smith.

| Fact | Importance |
|---|---|
| A Wraiths raider camp in the Badlands is empty now | 5 |
| A merc killed the raiders | 4 |
| The merc freed a captive nomad | 3 |
| The merc came on a motorcycle | 2 |

A "merc" is a person who does jobs for money. In the game, the player is a merc.

Examples for preset 1, with the event on day 41:
- On day 41, Regina knows all 5 facts.
- On day 41.4, Robert Wilson and Cassius Ryder know nothing.
- On day 41.5, Robert Wilson and Cassius Ryder know 3 facts.
- On day 42, Wakako Okada and Dino Dinovic know 2 facts: the hideout is gone, and a solo merc did it.
- Padre (Heywood), El Capitan (Santo Domingo), Mr. Hands (Pacifica) and Dakota Smith (Badlands) never know.

Examples for preset 2, with the event on day 41:
- On day 42, Dino, El Capitan and Mr. Hands know 2 facts: the fight, and the two dead officers.
- Regina, Robert Wilson, Cassius, Wakako and Dakota never know.

Examples for preset 3, with the event on day 41:
- On day 41, Dakota Smith knows all 4 facts.
- On day 42, Wakako Okada (Westbrook) and El Capitan (Santo Domingo) know 2 facts: the camp is empty, and a merc killed the raiders.
- Regina, Robert Wilson, Cassius, Dino, Padre and Mr. Hands never know.

## Constraints

- Put everything about one game in its world file or its mod. Never in the engine code.

## Planned Changes

| Ticket | Summary |
|---|---|
| #7 | A mod sends its own world to the engine. The first mod's world is in the mod's specs. |
| #8 | NPCs that a mod adds while the game runs, not only NPCs from the world file. |
