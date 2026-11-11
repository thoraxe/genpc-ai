# The Cyberpunk World

The mod sends this world to the engine when the game starts. It describes Night City: its districts (towns), their neighbours, a starter cast and the setting text. The engine rules for a world are in the engine spec (`.ai/spec/what/world-file.md`).

## Behavioral Rules

### Towns, places and NPCs

1. The Cyberpunk world file is `mods/cyberpunk/world.json`. The mod ships it.
2. The Cyberpunk world has 7 towns. Each town is a district of Night City.
3. Each town lists its next towns in this table. Each link is in both towns. (owner question 3)

| Town (`id`) | Next towns |
|---|---|
| Watson (`watson`) | City Center, Westbrook |
| Westbrook (`westbrook`) | Watson, City Center, Badlands |
| City Center (`city_center`) | Watson, Westbrook, Heywood, Santo Domingo |
| Heywood (`heywood`) | City Center, Santo Domingo, Pacifica |
| Santo Domingo (`santo_domingo`) | City Center, Heywood, Pacifica, Badlands |
| Pacifica (`pacifica`) | Heywood, Santo Domingo |
| Badlands (`badlands`) | Westbrook, Santo Domingo |

4. The Cyberpunk world file has no Dogtown. An event in Dogtown goes only to its witnesses (engine `knowledge.md` rule 5a). (owner question 2)
5. Each part of a district is a place. It belongs to its district. (owner question 6)

| Place (`id`) | Town |
|---|---|
| Little China (`little_china`), Kabuki (`kabuki`), Northside (`northside`), Arasaka Waterfront (`arasaka_waterfront`) | Watson |
| Japantown (`japantown`), Charter Hill (`charter_hill`), North Oak (`north_oak`) | Westbrook |
| Corpo Plaza (`corpo_plaza`), Downtown (`downtown`) | City Center |
| The Glen (`the_glen`), Wellsprings (`wellsprings`), Vista del Rey (`vista_del_rey`) | Heywood |
| Arroyo (`arroyo`), Rancho Coronado (`rancho_coronado`) | Santo Domingo |
| Coastview (`coastview`), West Wind Estate (`west_wind_estate`) | Pacifica |

Example: an event in Kabuki counts as an event in Watson. Gossip goes to City Center and Westbrook.

6. The starter cast has these 9 NPCs. (owner question 1)

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

7. Each Cyberpunk NPC `id` will be the game's record ID: the fixed name of the character in the game data. The mod uses this ID to find the NPC. We must still confirm the IDs in the game.
8. Each NPC in the starter cast has a `voice_id`. The table in rule 8c gives the voices. [PLANNED: #12]
8a. Each voice is a premade voice: a voice that the voice service itself gives. Every account can use premade voices. This includes the tester's account. [PLANNED: #12]
8b. The world file has a voice list for added NPCs: 3 female and 3 male premade voices. (owner question 5) [PLANNED: #12]
8c. The code stage adds a table with the name and `voice_id` of each voice. The owner listens to them and can change them before the merge. [PLANNED: #12]
9. The Cyberpunk setting text is this:

> Speak like a person who lives in Night City in the year 2077. Night City is a hard, dangerous city. Corporations and gangs control it. Use some street words, but keep your meaning clear.

10. In the Cyberpunk world file, next-town gossip arrives after 1 day (`hop2_delay_days` = `1.0`). Example: event on day 41, gossip on day 42. (owner question 4)
11. The Cyberpunk world file does not change the other knowledge settings.

### How the mod gives the world to the engine

12. When the game starts, the mod sends this world to the engine (engine `http-api.md` rule 8a).
13. The world name (`id`) is `cyberpunk`.
14. The world starts at day 0 (`start_day` = `0`). A new game starts at hour 0.
15. The general description for added NPCs is: "You are an ordinary person in Night City. You have no special story." (owner question 7)

### The Cyberpunk presets (`mods/cyberpunk/events.json`)

16. The Cyberpunk preset file has 3 presets. Only the tests use it. The tests send each preset in the full form (engine `http-api.md` rule 13).

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

- The world has no paid content (Phantom Liberty).
- The world changes no engine rule. It only gives data in the world file format.

## Planned Changes

| Ticket | Summary |
|---|---|
| #7 | The first version of the Cyberpunk world. |
| #12 | Voices for the starter cast, and a voice list for added NPCs. |
