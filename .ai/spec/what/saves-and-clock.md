# Saves and Clock

The clock is the day in the game. Saves keep a copy of everything that NPCs know. When the player loads a save, every NPC knows only what it knew at that save.

## Behavioral Rules

### Clock

1. The clock starts at the start day (`POC_START_DAY`, default `41`).
2. The clock only moves forward. To go back in time, load a save.
3. One clock move is more than 0 days and a maximum of 365 days.
4. When the clock moves, gossip that is due arrives (see `knowledge.md` rule 16). The engine gives back the new memories.
5. Memories fade by the clock, not by the real time.

Example: the clock is at day 41. The mod moves it by 0.5 days. The clock is now at day 41.5, and Torvald gets the gossip.

### Events

6. An event happens on the current day of the clock.
7. Each witness must be a known NPC. If the mod sends an unknown witness, the engine refuses the event.
8. Each event that the mod sends is a new event. The engine gives it a new name, for example `embershard_cleared@41#1`. If the mod sends the same event two times, the engine stores two events.
9. When the engine stores an event, the witnesses get their memories. Gossip that is already due also arrives.

### Saves

10. A save keeps a copy of all events, memories, conversation turns and the clock.
11. A save also keeps which recent news each NPC told, and how many recalls each memory has.
12. Each save has a label. If the mod gives no label, the label is "Day N" (for example, "Day 41.5").
13. When the player loads a save, the engine removes all events, memories, turns and the clock. Then it puts back the copy from the save.
14. After a load, nothing from after the save stays. This includes memories, conversations and facts from the player.
15. A load does not remove saves. The player can load a different save later.

### Reset

16. A reset removes all events, memories and turns. It sets the clock to the start day.
17. A reset does not remove saves.

Examples:
- If the player saves on day 41, moves to day 41.5, and talks to Torvald, then Torvald knows about the bandits.
- If the player then loads the day-41 save, then Torvald knows nothing about the bandits. He also does not remember the conversation.
- If the player tries to move the clock back by 2 days, then the engine refuses.
- If the player resets, then the saves are still in the list.

## Constraints

- A save must keep everything that can change what an NPC knows or says. If you add new stored data, add it to the save.
- A test must prove that a load removes the new data from after the save.

## Planned Changes

| Ticket | Summary |
|---|---|
| #9 | A mod can set the clock to the game's own day. |
| #11 | A save uses a name that the game gives. Then a game load can load the matching engine save. |
| #14 | The Cyberpunk mod saves and loads engine knowledge with the game's own saves. |
