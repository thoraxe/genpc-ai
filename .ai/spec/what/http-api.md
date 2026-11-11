# HTTP API

The HTTP API is how a mod talks to the engine. The test page uses the same API. A mod sends a request to an address (a "route"). The engine sends an answer in JSON (a text format for data).

The engine runs at `http://localhost:8000` by default.

## Behavioral Rules

### General

1. Every route is the same for every game. No route has a game name in it.
2. The routes and the fields in their answers are an agreement with the mods. You can add a new field.
2a. Do not rename or remove a field without a note in the PR and a change in the mod.
3. If a request names an unknown NPC, save, turn or preset, the engine answers with error `404` ("not found").
4. If a value is outside its permitted range, the engine answers with error `400` ("bad request"). Rules 9, 10b, 14 and 19 give the ranges.
4a. If a field is missing or has the wrong type, the engine answers with error `422`. Example: an `importance` of 9.

### Start

5. `POST /api/session/start` tells the mod what the engine can do. The answer has:
   - `protocol`: the version of the API. It is `1` now.
   - `capabilities`: what the engine can do.
     - `max_choices`: the maximum number of choices (`3`).
     - `free_text`: the player can type free text (`true`).
     - `audio`: the sound format of the voice. It is empty if there is no voice.
     - `audio_slots`: the number of slot files that the engine can write. It is `0` if the voice is off, or if there is no slot folder.
   - `llm`: the name of the AI model. Before the first conversation, it is the model name only. After it, it is the model name and the service address.
   - `tts`: the name of the voice service, or empty.
   - `world`: the `id` of the world in use (`world-file.md` rule 16r).

### World

6. `GET /api/world` gives the full world: the day, towns, places, NPCs, events, presets, saves and knowledge settings.
6a. The answer also gives the `id` of the world in use (`world`).
7. For each NPC, the answer gives the number of memories that the NPC did not forget (`known`).
8. This answer does not give the NPC's description. The inspector route gives it (rule 20).
8a. `POST /api/world` sends a world to the engine. The body is the world, in the same format as the world file.
8b. The answer gives the world `id`, the number of towns and the number of NPCs. Example: `harbor_city`, 3 towns, 5 NPCs.
8c. If the world is not correct (`world-file.md` rule 16n), the engine answers with `400`. The answer tells why.
8d. Rule 8c uses `400`, not `422`, also for a missing part. The world in use stays.

### Clock

9. `POST /api/clock/advance` with `days` moves the clock forward. `days` must be more than 0 and a maximum of 365.
10. The answer gives the new day and the memories that arrived (`new_memories`).
10a. `POST /api/clock/set` with `hours` sets the clock from the game's hours (see `saves-and-clock.md` rules 5a–5g).
10b. `hours` must be 0 or more. The new day must be a maximum of 365 days after the clock. (owner question 3)
10c. If the new day is earlier than the clock, the engine answers with error `400`.
10d. The answer gives the day of the clock and the memories that arrived (`new_memories`).
10e. If nothing changes, `new_memories` is empty. If the engine refuses, the answer still gives the day of the clock.

### Events

11. `POST /api/events` tells the engine about an event. Use one of two forms.
12. **Preset form:** send `preset` (the name of an event in `poc/data/events.json`). You can also send `witnesses`. If you send no `witnesses`, the engine uses the preset's default witnesses.
12a. In a mod world, the preset form answers with `404`. Presets belong only to the test world.
13. **Full form:** send these fields:
   - `type`: a short tag, for example `location_cleared`;
   - `location`: a place or a town;
   - `facts`: each with `text` and `importance`;
   - `witnesses`.
13a. The engine does not check `location`. If the place or town is not in the world file, only the witnesses know the event.
14. A request without a preset must have `type`, `location` and `facts`. If one is missing, the engine answers with `400`.
15. The answer gives the stored event and the memories that it made (`new_memories`).

### Conversation

16. `POST /api/dialog/open` with `npc_id` starts a conversation with a greeting. The answer is one turn (see `conversation.md` rule 27).
17. `POST /api/dialog/choose` with `npc_id`, `session_id` and `text` sends what the player says. The answer is the next turn.
18. `session_id` is the conversation number from the greeting turn.
19. `text` must have a maximum of 500 characters, and it must not be only spaces. The engine then removes spaces at the start and the end.

### Inspector

20. `GET /api/npc/{npc_id}/knowledge` shows all the memories of one NPC, the strongest first. It also shows the NPC's description and the last 12 turns.
21. For each memory, the answer shows:
   - its strength, and if it is clear, vague or forgotten (`stage`);
   - the facts that it keeps (`kept`);
   - the faded facts (`faded`);
   - the lost facts (`lost_in_retelling`).
22. `GET /api/npc/{npc_id}/prompt` shows the prompt that the NPC will get in the next turn. It does not call the AI model.

### Saves

23. `POST /api/saves` with an optional `label` makes a save. The answer gives the new save number and the list of all saves.
24. `POST /api/saves/{save_id}/load` loads a save. The answer gives the day of the save.
25. `POST /api/reset` resets the world. The answer gives the start day.

### Test page

26. `GET /` gives the test page.

### Voice

27. `GET /api/audio/{turn_id}` gives the voice of the NPC's line in that turn. The sound arrives in parts, so it can start to play before it is complete.
28. The engine answers with `404` in these cases:
   - the voice is off;
   - the turn is unknown;
   - the NPC has no voice.
29. For `GET /api/audio`, the engine makes the voice again for each request. It does not keep that sound. Slot files are different (rules 30a–30n).
30. A world-file NPC has its own voice, from `voice_id` in the world file. An added NPC gets a voice from the voice list (rule 42).

**Slot files**

30a. `POST /api/audio/{turn_id}/slot` puts the voice of the NPC's line into a slot file.
30b. A slot file is a sound file with a fixed name in the slot folder. The mod plays them with a sound tool of its game. The mod tells that tool the names before the game starts.
30c. The slot files have the names `genpc_voice_1.mp3` to `genpc_voice_N.mp3`. `N` is the setting `AUDIO_SLOT_COUNT`. Example: with `4`, the last file is `genpc_voice_4.mp3`.
30d. Each request uses the next slot file. After the last slot file, the engine uses slot file 1 again. (owner question 3)
   - Example with 4 slot files: turns 12, 13, 14, 15 and 16 get slots 1, 2, 3, 4 and 1.
   - A second request for the same turn is a new request. The engine makes the voice again and uses the next slot file.
30e. Each request gets a different slot file, also if two requests arrive at the same time.
30f. The engine writes the full voice, and then it answers. The mod never gets a slot file with only part of the voice. (owner question 2)
   - The subtitle does not wait for this answer. The mod shows the line immediately. The voice comes about 1 second later.
30g. The answer gives these fields:
   - `turn_id`: the turn number.
   - `slot`: the name of the slot file without `.mp3`, for example `genpc_voice_2`.
   - `file`: the full path of the slot file.
30h. When the engine starts again, it uses slot file 1 first.

**When the engine does not write a slot file**

30i. The engine answers with `404` and changes no slot file in these cases:
   - the voice is off (rule 28);
   - the turn is unknown;
   - the NPC has no voice;
   - the setting `AUDIO_SLOT_DIR` is empty;
   - the slot folder is not there.
30j. If the voice service fails, the engine answers with `502` ("bad gateway"). The slot file keeps its old sound.
30k. A failed request also uses its slot file in the rotation. Example: turn 14 fails on slot 3. Then turn 15 gets slot 4.
30l. The engine does not make the slot folder.
30m. If the engine cannot write the slot file, it answers with `503`. The answer tells why. The old file stays. Example: the game has the file open.

**The test page**

30n. A slot request does not change `GET /api/audio/{turn_id}`. The test page still gets the voice as a stream (rule 27).

### NPCs

31. Send `POST /api/npcs` before each greeting. It tells the engine which NPC the player talks to.
32. The request has these fields:

| Field | What it is | Required | Example |
|---|---|---|---|
| `record_id` | The record ID of a named or world-file NPC. 1 to 100 characters. | one of the two | `npc.harbor_vendor` |
| `entity_id` | The entity ID of a crowd NPC. Only digits, 1 to 20 of them. | one of the two | `1874320956` |
| `name` | The name that the player sees. 1 to 60 characters. | yes | `Bram` |
| `settlement` | The town `id` from the world file. 1 to 60 characters. | yes | `riverwood` |
| `role` | The job. Optional. A maximum of 40 characters. | no | `noodle vendor` |
| `faction` | The faction. Optional. A maximum of 40 characters. | no | `Harbor Guild` |
| `gender` | `female` or `male`. Optional. | no | `male` |

33. Send `record_id` for a named NPC. Send `entity_id` for a crowd NPC.
34. If the request has both `record_id` and `entity_id`, or has neither, the engine answers with `400`. This is also true for a missing `name` or `settlement`. Rules 34–35c use `400`, not `422`.
35. If `name`, `settlement`, `role`, `faction` or `gender` is not in its range in rule 32, the engine answers with `400`.
35a. If `name`, `settlement`, `role` or `faction` has a line break, the engine answers with `400`.
35b. If `record_id` is empty or has more than 100 characters, the engine answers with `400`. This is also true if it starts with `crowd-`, or has a `/` or a line break.
35c. If `entity_id` is not a whole number with 1 to 20 digits, the engine answers with `400`. Example: `"5/6"` is not correct.
36. If `record_id` is the `id` of a world-file NPC, the engine uses that NPC. It changes nothing.
37. Else, the engine adds the NPC. If the engine added this NPC before, it changes the details to the new ones.
38. The answer gives `npc_id`. Use it in later requests. Example: `npc.harbor_vendor` or `crowd-1874320956`.
39. The answer gives `kind`: `world`, `named` or `crowd`.
40. After the mod sends `POST /api/npcs`, the NPC is a known NPC. Events, conversations, voice and the inspector accept its `npc_id`.
41. `GET /api/world` also lists the added NPCs. Each NPC in the list has its `kind`.
42. An added NPC gets its voice from the voice list (see `world-file.md` rules 7a–7d).

Examples:
- If a mod sends `POST /api/clock/advance` with `days` = `-2`, then the engine answers with `400`.
- In a world with 24-hour days: if the clock is at day 41.5 and a mod sends `POST /api/clock/set` with `hours` = `984`, then the engine answers with `400`.
- If a mod sends `POST /api/dialog/open` for an NPC that is not in the world file, then the engine answers with `404`.
- If there is no `ELEVENLABS_API_KEY`, then `GET /api/audio/7` answers with `404`, and `/api/session/start` gives an empty `tts`.
- If a mod sends `POST /api/npcs` with `record_id` = `torvald`, then the answer gives `kind` = `world`.
- If a mod sends `POST /api/npcs` with no `record_id` and no `entity_id`, then the engine answers with `400`.
- If a mod sends `POST /api/dialog/open` for `crowd-1874320956` before the mod sends `POST /api/npcs`, then the engine answers with `404`.
- If a mod sends `POST /api/audio/12/slot` and the next slot is 1, then the answer gives `slot` = `genpc_voice_1`.
- If a mod asks for 5 slot voices with 4 slot files, then the fifth voice goes into `genpc_voice_1.mp3`.
- With 4 slot files, turns 12 and 13 used slots 1 and 2. Thus turn 14 gets slot 3. If the voice service fails for turn 14, then the answer is `502`, and `genpc_voice_3.mp3` keeps its old sound.

## Constraints

- The API is for one computer only. It has no login.
- The engine makes changes to knowledge and conversations one at a time. If two requests change them at the same time, one waits for the other.

## Planned Changes

| Ticket | Summary |
|---|---|
| #7 | `POST /api/world`: a mod sends its world to the engine. |
| ~~#8~~ | A route to add NPCs while the game runs. |
| #9 | `POST /api/clock/set`: set the clock from the game's own day. |
| ~~#10~~ | `POST /api/audio/{turn_id}/slot`: the voice goes into a slot file that the mod can play. |
| #11 | Saves and loads by a name that the game gives (`/api/saves/{token}/load`). |
