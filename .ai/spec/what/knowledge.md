# Knowledge

Knowledge decides which NPC knows which facts. It also decides how well each NPC remembers them. It uses only fixed rules and numbers. It never asks the AI model.

All numbers below are the defaults. The world file can change them (see `world-file.md`). The name in `code` style is the setting name.

## Behavioral Rules

### Witnesses

1. A witness gets all the facts of the event, on the day of the event.
1a. An added NPC can be a witness of an event after the mod adds it. `[PLANNED: #8]` (owner question 2)
2. A witness memory starts at full strength (`1.0`).

Example: Hrolf sees the bandits die on day 41. On day 41 he knows all 5 facts: the bandits are dead, the steel armor, the loot, the war axe, and dusk.

### Gossip

3. Gossip goes only to NPCs who are not witnesses and do not know the event yet.
4. An NPC gets a maximum of one memory for each event. A witness never also gets gossip about it.
5. An event in a place counts as an event in the town of that place. An event in a town counts as an event in that town.
5a. If the place or town of the event is not in the world file, no gossip goes out. Only the witnesses know the event.
5b. An added NPC gets gossip like a world-file NPC. Its town is the town that the mod sent. `[PLANNED: #8]` (owner question 1)
5c. When the engine adds an NPC, the NPC also gets the gossip of earlier events that is already due. `[PLANNED: #8]`
   Example: an event in Riverwood on day 41. The mod adds Bram in Riverwood on day 42. His memory has day 41.5.
5d. If the town of an added NPC is not in the world file, the NPC gets no gossip. `[PLANNED: #8]`
5e. If the mod sends a new town for a named NPC, the NPC keeps all its memories. `[PLANNED: #8]` (owner question 3)
5f. After the move, gossip goes to the named NPC by its new town. This includes gossip of earlier events. `[PLANNED: #8]` (owner question 3)
5g. A world-file NPC keeps the town from the world file. The engine does not use the town from the mod. `[PLANNED: #8]`
6. **Same town:** gossip goes to every NPC in the town of the event after half a day (`hop1_delay_days` = `0.5`).
7. Same-town gossip keeps only facts of importance 3 or more (`hop1_min_importance` = `3`).
8. Same-town gossip starts at strength `0.8` (`hop1_salience`).
9. **Next town:** gossip goes to every NPC in each next town after 3 days (`hop2_delay_days` = `3.0`).
10. Next-town gossip keeps only facts of importance 4 or more (`hop2_min_importance` = `4`).
11. Next-town gossip starts at strength `0.6` (`hop2_salience`).
12. Gossip does not go further than the next towns.
13. If no fact has a high enough importance, no gossip goes to that group.
14. Gossip does not carry the facts below its importance limit. These are lost facts. The NPC never gets them from that gossip.
15. The day of a gossip memory is the day it arrives, not the day the engine finds it. Example: an event on day 41, and the clock jumps to day 50. Torvald's memory has day 41.5, so it is already 8.5 days old.
16. Gossip arrives when the clock moves forward, and when a mod sends an event.

Example: the bandits die at Embershard Mine on day 41. The mine belongs to Riverwood. Whiterun is the next town.
- On day 41.4, Torvald (Riverwood) knows nothing.
- On day 41.5, Torvald knows 3 facts: the bandits are dead, the steel armor, the loot.
- On day 44, Eirik (Whiterun) knows 2 facts: the bandits are dead, the steel armor.
- Sabine (Solitude) never knows. Solitude is not a next town of Riverwood.

### Fading

17. Each memory has a strength. The strength gets smaller as days pass.
18. Strength = start strength × e^(−`0.08` × age in days) × (1 + recall boost). (`decay_lambda` = `0.08`.)
19. Each recall adds `0.25` to the recall boost (`recall_boost`). The recall boost is never more than `0.5` (`recall_cap`). Thus 2 recalls give the maximum.
20. A memory is **clear** if its strength is `0.35` or more (`gist_threshold`). The NPC knows all its facts.
21. A memory is **vague** if its strength is less than `0.35`. The NPC keeps only facts of importance 3 or more (`gist_min_importance`). The other facts are faded facts.
22. A memory is **forgotten** if its strength is less than `0.05` (`forget_threshold`). The NPC knows none of its facts.
23. A vague memory tells the AI model that the NPC "only vaguely remembers".

Example, with no recalls:

| Memory | Vague after | Forgotten after |
|---|---|---|
| Witness (start `1.0`) | 13.1 days | 37.4 days |
| Same-town gossip (start `0.8`) | 10.3 days | 34.7 days |
| Next-town gossip (start `0.6`) | 6.7 days | 31.1 days |
| A fact from the player (start `1.0`) | 13.1 days | 37.4 days |

With 2 or more recalls, a witness memory becomes vague after 18.2 days and forgotten after 42.5 days.

### Which memories go to the AI model

24. The engine never sends a forgotten memory to the AI model.
25. The engine sends a maximum of 5 memories in one turn (`retrieval_k`). It chooses the strongest ones.
26. Recent news always goes first. Recent news is a memory of an event that the NPC did not tell yet. The NPC got it less than 3 days ago (`news_window_days`).
27. A maximum of 2 recent news memories get this first place (`news_slots`).
28. The engine sends only the facts that the NPC still has. It never sends lost facts or faded facts.

### What the NPC learns from the player

29. An NPC remembers a fact about the player only if the player really said it in this conversation.
29a. A crowd NPC never keeps a fact from the player. `[PLANNED: #8]`
30. The engine checks each fact that the AI model wants to remember. It finds the key words in the fact. A key word has 4 or more letters and is not a common word ("the", "about", "player" and others).
31. The engine keeps the fact only if half or more of its key words are in the player's words. It uses all the player's words in this conversation.
32. The engine does not keep a fact that has no key words.
33. A fact from the player starts at full strength (`1.0`). It fades like all other memories.

Examples:
- The player says "My name is Lydia and I am from Falkreath." The AI model wants to remember "The player is named Lydia". The engine keeps it.
- The player says "Hello." The AI model wants to remember "The player is a dragon slayer". The engine does not keep it.

## Configuration Surface

These settings are in the `rules` part of the world file. See rules above for each one.

| Setting | Default | Rule |
|---|---|---|
| `decay_lambda` | `0.08` | 18 |
| `recall_boost` | `0.25` | 19 |
| `recall_cap` | `0.5` | 19 |
| `gist_threshold` | `0.35` | 20, 21 |
| `gist_min_importance` | `3` | 21 |
| `forget_threshold` | `0.05` | 22 |
| `hop1_delay_days` | `0.5` | 6 |
| `hop1_min_importance` | `3` | 7 |
| `hop1_salience` | `0.8` | 8 |
| `hop2_delay_days` | `3.0` | 9 |
| `hop2_min_importance` | `4` | 10 |
| `hop2_salience` | `0.6` | 11 |
| `retrieval_k` | `5` | 25 |
| `news_window_days` | `3.0` | 26 |
| `news_slots` | `2` | 27 |

## Constraints

- The knowledge rules never use chance, the real clock, or the AI model. They use only the stored events, the day in the game, and the settings above.
- Each change to a knowledge rule needs a test that checks the exact numbers.
- A lost fact must never go into the prompt. A forgotten memory must never go into the prompt.
