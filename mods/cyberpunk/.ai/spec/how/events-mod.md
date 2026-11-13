# Events Mod (code map)

The code that builds `what/events.md`: fights, gigs and police chases go to the engine as events, and the engine's clock follows the game's clock. It talks to the engine only through the HTTP API.

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `r6/scripts/genpc/Events.reds` | `GenpcEvents` | The clock, the current fight, the current chase, gigs, witnesses and the send queue. |
| `r6/scripts/genpc/Events.reds` | `GenpcVictim`, `GenpcWitness`, `GenpcGroup`, `GenpcOutEvent` | Data: one victim, one witness (with its `/api/npcs` body), one group of a fight, one event to send. |
| `r6/scripts/genpc/Events.reds` | `@wrapMethod(PlayerPuppet) OnTargetNeutraliziedEvent`, `OnDeath` | Kills and knock-outs by the player; the player's death. |
| `r6/scripts/genpc/Npc.reds` | `PlaceId`, `PartId`, `PlaceName`, `Kind`, `FactionName`, `NpcBody` | Place ids (rules 5–5c), fact names, the kind and faction of a victim, the NPC body for a conversation and for a witness. |
| `r6/scripts/genpc/System.reds` | `SendClock`, `Settings` | The talk system sends the clock after the world at a load and before each greeting. `GenpcEvents` reads the settings from it. |
| `r6/scripts/genpc/Settings.reds` | `eventsOn` | "Send game events". |
| `tests/test_events.py` | | The "who knows what" examples against the engine, and checks of the script. |

## Data Flow

1. `Session/Ready` → `GenpcEvents.OnSessionReady`: drops the open fight, the open chase and the queue; registers the stars listener (`UI_WantedBar.CurrentWantedLevel`) and the journal callback; starts the 1 s tick.
2. `OnTick` (1 s, not in a menu): counts `playSeconds`; `KeepPlace`; `SendClock("timer")` each 60 s; `CheckFightEnd`; `Drop("setting off")` when `eventsOn` is false.
3. Kill: the game calls `PlayerPuppet.OnTargetNeutraliziedEvent` only when the player is the killer (`ScriptedPuppet.RewardKiller`). → `OnNeutralized`: starts the fight (place, hour), adds or updates the `GenpcVictim`, removes it from the witnesses, `FindWitnesses`.
4. `CheckFightEnd` → `SendFight`: groups the victims by kind and faction, makes the facts (`Verb`, `Noun`, `Importance`, `TimeFact`) → `Queue`.
5. Stars: `OnStars` starts a chase at the first star (place, witnesses), keeps the highest stars, and at 0 stars calls `SendChase` if the highest was 2 or more.
6. Journal: `OnJournalState` for `gameJournalQuest` → `Succeeded` and `IsGig` → a `gig` event without witnesses.
7. `Queue` adds the witness fact (not for a gig) and calls `SendNext`. One event at a time: `POST /api/npcs` for each witness (`OnWitness`), then `POST /api/clock/set` (`OnEventClock`), then `POST /api/events` (`OnEventSent`). A 10 s `GenpcEventTimeout` for the whole event.

## Key Abstractions

- **Kinds.** `GenpcNpc.Kind`: 0 = a faction, 1 = police (`IsCharacterPolice` or `NCPD`), 2 = ordinary people (civilian, crowd, `Civilian`, `Unaffiliated`), 3 = not known. A faction without a name becomes 3 (rule 7c).
- **Witness data is kept at once.** `GenpcWitness.body` is made when the NPC is found, because the NPC can be gone when the event is sent.
- **Lists are returned, not changed in place.** `FindWitnesses` and `WithoutWitness` return a new array.
- **Tokens.** Each event has a `token`. Answers and the timeout with another token do nothing.

## Integration Points

| Consumer | Provider | Mechanism |
|---|---|---|
| `GenpcEvents` | engine | RedHttpClient `PostJson`: `/api/clock/set`, `/api/npcs`, `/api/events` |
| `GenpcEvents` | game | `TimeSystem.GetGameTimeStamp`, `GameTime.Hours`, `TargetingSystem.GetTargetParts` (`TSF_NPC`, 20 m), `JournalManager.RegisterScriptCallback`, `UI_WantedBar` blackboard |
| `GenpcSystem` | `GenpcEvents` | `GenpcEvents.Get(game).SendClock(why)` |
| `GenpcEvents` | `GenpcSystem` | `Settings()` |

## Implementation Notes

- **Game hours** are `GetGameTimeStamp() / 3600`. A new game does not start at hour 0 of the game's clock, so the first clock is already some hours in.
- **Redscript 0.5 has no `continue`.** The compiler (`scc`) can also hang after an error: run it with a time limit.
- **The journal after a load.** Callbacks in the first 10 s after `Session/Ready` are ignored, and each gig is sent one time per play (`gigsSent`).
- **Not verified in the game yet:** that a kill with a car names the player; that `GetGameTimeStamp` counts from the start of the game; that `GetTitle` gives readable text; which journal type each gig and side job has; the faction names from `LocalizedName`.
- The engine does not check that the world is `cyberpunk` before an event. After an engine restart, the first greeting or load sends the world again (`talk.md` rule 2a).
