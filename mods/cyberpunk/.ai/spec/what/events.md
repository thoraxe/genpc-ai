# Game Events and the Clock

The game tells the engine what happens: fights, finished gigs and police chases. The engine then decides who knows it (engine `knowledge.md`). The mod also keeps the engine's clock the same as the game's clock, so gossip arrives and memories fade with game time. [PLANNED: #13]

Words in this file:
- **game hours:** the number of hours of game time since the player started a new game. When the player sleeps or waits in the game, the game hours go up.
- **fight:** the kills and knock-outs by the player from the first one until the fight ends (rule 6).
- **gig:** a task in the game's journal that is a gig from a fixer or a side job. A main story task is not a gig.
- **police chase:** the time when the police want the player. The game shows 1 to 5 stars.
- **witness range:** 20 metres around the player.
- **place id:** the `id` of a place or a town in the Cyberpunk world file. Example: `northside`, `watson`.

## Behavioral Rules

### Clock

1. After the mod sends the world at a load (`talk.md` rule 1), it sends the game hours (engine `http-api.md` rule 10a). [PLANNED: #13]
2. The mod also sends the game hours every 60 seconds of play, before each event and before each greeting. [PLANNED: #13]
3. One engine day is 24 game hours. [PLANNED: #13]
   Note for testers: game time goes about 8 times faster than real time. Same-town gossip comes 12 game hours after an event: about 1.5 hours of real play. Sleep or wait in the game to make it come sooner.
4. If the engine refuses the game hours because they are earlier than its clock (engine `saves-and-clock.md` rule 5e), the mod goes on. The clock of the engine stays where it was until the game hours are later again. (owner question 5) [PLANNED: #13]
   Example: the player dies and loads a save from 10 game minutes before. For those 10 game minutes, no gossip arrives. The NPCs keep what they learned after the save, until #14.
   Example: the player plays until day 30, then loads a save from day 10. For 20 game days (about 60 hours of real play) no gossip arrives and no memory fades. Events in that time happen on day 30 for the engine. #14 removes this problem.
4a. A new game is the same as a load of a very old save (rule 4). Until #14, the NPCs keep their memories from the earlier game.

### Place of an event

5. The mod sends the place id of the part of the district where the event happens. Example: `northside`. [PLANNED: #13]
5a. If that part is not in the world file, the mod sends the place id of the district. Each area of the Badlands is the town `badlands` (`talk.md` rule 13a).
5b. If the game gives no district, the mod uses the last district that the game gave in this play. If there is none, it uses `watson` (`talk.md` rule 13b).
5c. A Phantom Liberty area (Dogtown) is not in the world file. The mod sends its name as the game gives it. Only the witnesses know the event (engine `knowledge.md` rule 5a).

### Fights

6. When the game names the player as the killer of an NPC, the mod counts it in the current fight. This includes a kill with a car, a quickhack or a grenade. A kill by another NPC that fights with the player does not count. A knock-out counts in the same way. [PLANNED: #13]
6a. The fight ends when the player is not in combat and 60 seconds passed after the last kill or knock-out. The 60 seconds are seconds of play. They do not go on while the game is paused or a menu is open. [PLANNED: #13]
6b. When the fight ends, the mod sends one event for the whole fight, with `type` = `fight`. [PLANNED: #13]
    Example: if the player kills 4 Maelstrom members in 2 minutes, then the mod sends one event, not 4.
6c. When the game loads a save or the player dies, the mod drops the current fight. It sends no event for it. [PLANNED: #13]
    Example: if the player kills 2 Maelstrom members, dies and loads a save, then the mod sends no event.
6d. If the player turns "Send game events" off during a fight (rule 24), the mod drops the fight.
7. The fight event has one fact for each faction. The kind of faction and the number of NPCs set the importance. (owner question 4) [PLANNED: #13]

| Who | Fact | Importance |
|---|---|---|
| 1 or 2 members of one faction | "A merc killed 1 Tyger Claws member in Japantown." | 3 |
| 3 to 9 members of one faction | "A merc killed 4 Maelstrom members in Northside." | 4 |
| 10 or more members of one faction | "A merc killed 12 Valentinos members in Arroyo." | 5 |
| 1 or 2 police officers | "A merc killed 2 NCPD officers in Kabuki." | 4 |
| 3 or more police officers | "A merc killed 5 NCPD officers in Kabuki." | 5 |
| 1 or 2 ordinary people (no faction) | "A merc killed 1 ordinary person in Little China." | 4 |
| 3 or more ordinary people (no faction) | "A merc killed 3 ordinary people in Little China." | 5 |

7a. For a knock-out, the fact says "knocked out" and not "killed". If one faction has kills and knock-outs, the fact says "killed or knocked out" and gives the sum of both numbers. [PLANNED: #13]
7b. Each fight event also has a fact for the time of the first kill or knock-out. Importance 1, so only witnesses know it. [PLANNED: #13]

| Game time | Fact |
|---|---|
| 06:00 to 11:59 | "It happened in the morning." |
| 12:00 to 17:59 | "It happened in the afternoon." |
| 18:00 to 21:59 | "It happened in the evening." |
| 22:00 to 05:59 | "It happened at night." |

7c. If the mod does not know the faction of an NPC, the fact says "unknown people". The importance is the same as for a faction with that number of NPCs. [PLANNED: #13]
7d. The place in each fact is the place of the fight (rule 8).
8. The place of a fight is the place of the first kill or knock-out (rules 5–5c). [PLANNED: #13]
9. The mod does not count a kill or knock-out of a story character (`talk.md` rule 11). [PLANNED: #13]
9a. Kills and knock-outs in a main story task count as a fight. Only the end of the main story task sends no event (rule 11). [PLANNED: #13]

Example: if the player kills 3 Maelstrom members and 1 ordinary person in Northside at 23:00, then the event has 3 facts: "A merc killed 3 Maelstrom members in Northside." (4), "A merc killed 1 ordinary person in Northside." (4) and "It happened at night." (1).

### Gigs

10. When the game's journal marks a gig as done, the mod sends an event with `type` = `gig`. [PLANNED: #13]
11. These send no event: a main story task, a gig that failed, an NCPD scanner task, and a vehicle offer. (owner question 1) [PLANNED: #13]
12. The gig event has these facts: [PLANNED: #13]

| Fact | Importance |
|---|---|
| "A merc finished the gig 'Monster Hunt' in Little China." (the name that the journal shows) | 4 |
| The time fact (rule 7b), for the time when the gig is done | 1 |

13. The place of a gig is the place of the player when the gig is done (rules 5–5c). [PLANNED: #13]
13a. A gig event has no witnesses. The people near the player at that time did not see the gig. [PLANNED: #13]

### Police chases

14. A police chase ends when the stars go to 0. If the chase had 2 stars or more at any time, the mod sends an event with `type` = `police_chase`. A chase with only 1 star sends no event. (owner question 3) [PLANNED: #13]
14a. When the game loads a save or the player dies, the mod drops the current chase. It sends no event for it. [PLANNED: #13]
15. The chase event has these facts. The stars are the highest stars during the chase. [PLANNED: #13]

| Fact | Importance |
|---|---|
| "The NCPD chased a merc through Kabuki." (2 or 3 stars) | 3 |
| "The NCPD chased a merc through Kabuki." (4 or 5 stars) | 4 |
| "The merc got away." | 2 |

16. The place of a chase is the place of the player when the chase starts (rules 5–5c). [PLANNED: #13]
17. If a fight and a chase happen at the same time, the mod sends both events. [PLANNED: #13]

### Witnesses

18. The mod looks for witnesses at each kill or knock-out of a fight, and when a police chase starts. A witness is an NPC in witness range at that time. [PLANNED: #13]
19. A witness must be alive and awake, not hostile to the player and not a story character. An NPC that the player killed or knocked out in the fight is not a witness. [PLANNED: #13]
20. An event has a maximum of 5 witnesses. If the mod finds more, it keeps the 5 that were nearest to the player when it found them. [PLANNED: #13]
21. Before the mod sends the event, it adds each witness to the engine, the same as for a conversation (`talk.md` rules 9–14). A starter-cast NPC is a witness by its world-file `id`. [PLANNED: #13]
21a. If the engine refuses a witness, the mod leaves that witness out of the event. It sends the event with the other witnesses. [PLANNED: #13]
21b. Each fight event and chase event with a witness also has the fact "The merc was the person who is talking to you now." Importance 1, so only witnesses know it. (owner question 2) [PLANNED: #13]
    Example: if the player kills 3 Maelstrom members near a noodle vendor and then talks to the vendor, then the vendor can say: "I saw what you did to those Maelstrom guys."

### Who knows what (examples)

These follow from the engine's knowledge rules and `world.md` rule 10. The times count from the event.

- If the player kills 4 Maelstrom members in Northside (Watson) at night, and a noodle vendor sees it:
  - at once, the vendor knows all 3 facts: the kills, "at night", and that the player did it;
  - 12 game hours later, every NPC in Watson knows "A merc killed 4 Maelstrom members in Northside.";
  - 24 game hours later, every NPC in Westbrook and City Center knows it too;
  - NPCs in Pacifica, Heywood, Santo Domingo and the Badlands never know.
- If the player kills 1 Tyger Claws member in Japantown (Westbrook), then Westbrook NPCs know after 12 game hours. Importance 3 does not go to the next towns.
- If the player kills 3 Wraiths in Rocky Ridge (Badlands), then Badlands NPCs know after 12 game hours, and Westbrook NPCs know after 24 game hours.
- If the player finishes the gig "Monster Hunt" in Little China (Watson), then Watson NPCs know after 12 game hours, and Westbrook and City Center NPCs know after 24 game hours. A Pacifica NPC never knows.

### Not sent

22. The mod does not send an event when the player only goes into a new district. (owner question 6) [PLANNED: #13]

### Errors

23. If the engine does not answer an event in 10 seconds, or answers with an error, the event is lost. The mod writes this to the game log. The game goes on. [PLANNED: #13]

### Settings

24. The settings have "Send game events": on or off. The default is on. When it is off, the mod sends no event. It still sends the game hours. [PLANNED: #13]

### Log

25. For each event, the mod writes to the game log: the `type`, the place id, the facts, the number of witnesses, and the engine's answer. [PLANNED: #13]
26. When the engine refuses the game hours (rule 4), the mod writes this to the game log one time. It writes it again only after the engine accepted the game hours again. [PLANNED: #13]

## Constraints

- The mod sends only what the game shows the player. It never sends a story secret that the player has not seen.
- No paid content: Phantom Liberty areas and their gigs are not in the world file (rule 5c).

## Planned Changes

| Ticket | Summary |
|---|---|
| #13 | Fights, gigs and police chases go to the engine as events. The engine's clock follows the game's clock. |
| #14 | When the player loads a save, NPC knowledge goes back to that save. |
