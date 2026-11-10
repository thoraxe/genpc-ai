# HTTP API

The HTTP API is how a mod talks to the engine. The test page uses the same API. A mod sends a request to an address (a "route"). The engine sends an answer in JSON (a text format for data).

The engine runs at `http://localhost:8000` by default.

## Behavioral Rules

### General

1. Every route is the same for every game. No route has a game name in it.
2. The routes and the fields in their answers are an agreement with the mods. You can add a new field.
2a. Do not rename or remove a field without a note in the PR and a change in the mod.
3. If a request names an unknown NPC, save, turn or preset, the engine answers with error `404` ("not found").
4. If a value is outside its permitted range, the engine answers with error `400` ("bad request"). Rules 9, 14 and 19 give the ranges.
4a. If a field is missing or has the wrong type, the engine answers with error `422`. Example: an `importance` of 9.

### Start

5. `POST /api/session/start` tells the mod what the engine can do. The answer has:
   - `protocol`: the version of the API. It is `1` now.
   - `capabilities`: what the engine can do.
     - `max_choices`: the maximum number of choices (`3`).
     - `free_text`: the player can type free text (`true`).
     - `audio`: the sound format of the voice. It is empty if there is no voice.
   - `llm`: the name of the AI model. Before the first conversation, it is the model name only. After it, it is the model name and the service address.
   - `tts`: the name of the voice service, or empty.

### World

6. `GET /api/world` gives the full world: the day, towns, places, NPCs, events, presets, saves and knowledge settings.
7. For each NPC, the answer gives the number of memories that the NPC did not forget (`known`).
8. This answer does not give the NPC's description. The inspector route gives it (rule 20).

### Clock

9. `POST /api/clock/advance` with `days` moves the clock forward. `days` must be more than 0 and a maximum of 365.
10. The answer gives the new day and the memories that arrived (`new_memories`).

### Events

11. `POST /api/events` tells the engine about an event. Use one of two forms.
12. **Preset form:** send `preset` (the name of an event in `poc/data/events.json`). You can also send `witnesses`. If you send no `witnesses`, the engine uses the preset's default witnesses.
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
29. The engine makes the voice again for each request. It does not keep old sound files.
30. A world-file NPC has its own voice, from `voice_id` in the world file. An added NPC gets a voice from the voice list (rule 42). `[PLANNED: #8]`

### NPCs

31. Send `POST /api/npcs` before each greeting. It tells the engine which NPC the player talks to. `[PLANNED: #8]`
32. The request has these fields: `[PLANNED: #8]`

| Field | What it is | Required | Example |
|---|---|---|---|
| `record_id` | The record ID of a named or world-file NPC. | one of the two | `npc.harbor_vendor` |
| `entity_id` | The entity ID of a crowd NPC. | one of the two | `1874320956` |
| `name` | The name that the player sees. 1 to 60 characters. | yes | `Bram` |
| `settlement` | The town `id` from the world file. | yes | `riverwood` |
| `role` | The job. Optional. A maximum of 40 characters. | no | `noodle vendor` |
| `faction` | The faction. Optional. A maximum of 40 characters. | no | `Harbor Guild` |
| `gender` | `female` or `male`. Optional. | no | `male` |

33. Send `record_id` for a named NPC. Send `entity_id` for a crowd NPC. `[PLANNED: #8]`
34. If the request has both `record_id` and `entity_id`, or has neither, the engine answers with `400`. This is also true for a missing `name` or `settlement`. Rules 34–35a use `400`, not `422`. `[PLANNED: #8]`
35. If `name`, `role`, `faction` or `gender` is not in its range in rule 32, the engine answers with `400`. `[PLANNED: #8]`
35a. If `name`, `role` or `faction` has a line break, the engine answers with `400`. `[PLANNED: #8]`
36. If `record_id` is the `id` of a world-file NPC, the engine uses that NPC. It changes nothing. `[PLANNED: #8]`
37. Else, the engine adds the NPC. If the engine added this NPC before, it changes the details to the new ones. `[PLANNED: #8]`
38. The answer gives `npc_id`. Use it in later requests. Example: `npc.harbor_vendor` or `crowd-1874320956`. `[PLANNED: #8]`
39. The answer gives `kind`: `world`, `named` or `crowd`. `[PLANNED: #8]`
40. After the mod sends `POST /api/npcs`, the NPC is a known NPC. Events, conversations, voice and the inspector accept its `npc_id`. `[PLANNED: #8]`
41. `GET /api/world` also lists the added NPCs. Each NPC in the list has its `kind`. `[PLANNED: #8]`
42. An added NPC gets its voice from the voice list (see `world-file.md` rules 7a–7d). `[PLANNED: #8]`

Examples:
- If a mod sends `POST /api/clock/advance` with `days` = `-2`, then the engine answers with `400`.
- If a mod sends `POST /api/dialog/open` for an NPC that is not in the world file, then the engine answers with `404`.
- If there is no `ELEVENLABS_API_KEY`, then `GET /api/audio/7` answers with `404`, and `/api/session/start` gives an empty `tts`.
- If a mod sends `POST /api/npcs` with `record_id` = `torvald`, then the answer gives `kind` = `world`.
- If a mod sends `POST /api/npcs` with no `record_id` and no `entity_id`, then the engine answers with `400`.
- If a mod sends `POST /api/dialog/open` for `crowd-1874320956` before the mod sends `POST /api/npcs`, then the engine answers with `404`.

## Constraints

- The API is for one computer only. It has no login.
- The engine makes changes to knowledge and conversations one at a time. If two requests change them at the same time, one waits for the other.

## Planned Changes

| Ticket | Summary |
|---|---|
| #8 | A route to add NPCs while the game runs. |
| #9 | `POST /api/clock/set`: set the clock from the game's own day. |
| #10 | The voice goes into a sound file that a game mod can play, not only as a stream. |
| #11 | Saves and loads by a name that the game gives (`/api/saves/{token}/load`). |
