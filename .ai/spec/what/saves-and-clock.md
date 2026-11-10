# Saves and Clock

The clock is the day in the game. Saves keep a copy of everything that NPCs know. When the player loads a save, every NPC knows only what it knew at that save.

The engine sends the result of each change to the mod. For the exact fields, see `http-api.md`.

## Behavioral Rules

### Clock

1. The clock starts at the start day (`POC_START_DAY`, default `41`).
2. The clock only moves forward. To go to an earlier day, load a save.
3. One clock move is more than 0 days and a maximum of 365 days.
4. When the clock moves, gossip that is due arrives (see `knowledge.md` rule 16). The engine sends the new memories to the mod.
5. Memories fade by the clock, not by the real clock of the computer.

Example: the clock is at day 41. The mod moves it by 0.5 days. The clock is now at day 41.5, and Torvald gets the gossip.

### Events

6. An event happens on the current day of the clock.
7. Each witness must be a known NPC. If the mod sends an unknown witness, the engine refuses the event.
7a. An added NPC is a known NPC after the mod adds it (`http-api.md` rule 40). `[PLANNED: #8]`
8. Each event that the mod sends is a new event. The engine gives it a new name, for example `embershard_cleared@41#1`. If the mod sends the same event two times, the engine stores two events.
9. When the engine stores an event, the witnesses get their memories. Gossip that is already due also arrives.

### Saves

10. A save keeps a copy of all events, memories, conversation turns and the clock.
11. A save also keeps which recent news each NPC told, and how many recalls each memory has.
12. Each save has a label. If the mod gives no label, the label is "Day N" (for example, "Day 41.5").
12a. A save can have a save name. The mod chooses the save name. Example: `cp-1042`. `[PLANNED: #11]`
12b. A save name has 1 to 64 characters. Use only letters A–Z and a–z, digits, `-`, `_` and `.`. `[PLANNED: #11]`
12c. A save name must have one letter or more. Example: `cp-1042` is correct, and `1042` is not. `[PLANNED: #11]`
12d. If the mod saves with a save name that the engine has, the engine replaces that save. `[PLANNED: #11]`
12e. A replaced save keeps its save number. It gets the new copy, the new label and the new day. `[PLANNED: #11]`
12f. A save without a save name is always a new save. It never replaces a save. `[PLANNED: #11]`
13. When the player loads a save, the engine removes all events, memories, turns and the clock. Then it copies the save into their place.
13a. After a load, no crowd NPC exists. The engine removes them with their memories and turns. `[PLANNED: #8]`
13b. After a load, each added named NPC still exists. Its memories and turns come from the save. `[PLANNED: #8]` (owner question 4)
14. After a load, nothing from after the save stays. This includes memories, conversations and facts from the player.
14a. Exception: an added named NPC stays after a load. Its memories and turns come from the save. Its town stays the last town that the mod sent. `[PLANNED: #8]` (owner question 4)
15. A load does not remove saves. The player can load a different save later.
15a. The mod can load a save by its save name or by its save number. `[PLANNED: #11]`
15b. If no save has that save name, the engine changes nothing. It answers "not found" (`404`). `[PLANNED: #11]`
15c. The engine does not remove saves. If the player deletes a game save, the engine save stays. `[PLANNED: #11]`
15d. If a load by save name answers `404`, reset the engine. Then no NPC knows anything. `[PLANNED: #11]` (owner question 1)
15e. A load by save name treats NPCs that the mod added (#8) like a load by save number. See `saves-and-clock.md` rules 13a–13b. `[PLANNED: #11]` (owner question 2)

### Reset

16. A reset removes all events, memories and turns. It sets the clock to the start day.
16a. A reset removes all crowd NPCs. Added named NPCs stay, with no memories. `[PLANNED: #8]`
17. A reset does not remove saves.

Examples:
- If the player saves on day 41, moves to day 41.5, and talks to Torvald, then Torvald knows about the bandits.
- If the player then loads the day-41 save, then Torvald knows nothing about the bandits. He also does not remember the conversation.
- If the player tries to move the clock back by 2 days, then the engine refuses.
- If the player resets, then the saves are still in the list.
- The player saves on day 42, talks to a crowd NPC, and loads the save. Then the crowd NPC does not exist.
- If the mod saves as `quick-0` on day 41 and again on day 42, then a load of `quick-0` gives day 42. `[PLANNED: #11]`
- If the mod loads `cp-0007` and the engine has no such save, then the engine answers `404` and changes nothing. `[PLANNED: #11]`

## Constraints

- A save must keep everything that can change what an NPC knows or says. If you add new stored data, add it to the save.
- A test must prove that a load removes the new data from after the save.
- Exception: the list of added named NPCs is not part of a save (rule 14a). `[PLANNED: #8]`

## Planned Changes

| Ticket | Summary |
|---|---|
| #9 | A mod can set the clock to the game's own day. |
| #11 | A save uses a name that the game gives. Then a game load can load the matching engine save. |
| #14 | The Cyberpunk mod saves and loads engine knowledge with the game's own saves. |
