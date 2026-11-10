# HTTP API

The HTTP API is how a mod talks to the engine. The test web page uses the same API. A mod sends a request to an address (a "route") and gets an answer back in JSON (a text format for data).

The engine runs at `http://localhost:8000` by default.

## Behavioral Rules

### General

1. Every route is the same for every game. No route has a game name in it.
2. The routes and the fields in their answers are an agreement with the mods. You can add a new field. Do not rename or remove a field without a note in the PR and a change in the mod.
3. If a request names an unknown NPC, save, turn or preset, the engine answers with error `404` ("not found").
4. If a request has a value that is not permitted, the engine answers with error `400` ("bad request").

### Start

5. `POST /api/session/start` tells the mod what the engine can do. The answer has:
   - `protocol`: the version of the API. It is `1` now.
   - `capabilities`: what the engine can do.
     - `max_choices`: the maximum number of choices (`3`).
     - `free_text`: the player can type free text (`true`).
     - `audio`: the sound format of the voice. It is empty if there is no voice.
   - `llm`: the name of the AI model.
   - `tts`: the name of the voice service, or empty.

### World

6. `GET /api/world` gives the full world: the day, towns, places, NPCs, events, presets, saves and knowledge settings.
7. For each NPC, the answer gives the number of memories that the NPC did not forget (`known`).
8. The answer does not give the NPC's description. Only the prompt uses it.

### Clock

9. `POST /api/clock/advance` with `days` moves the clock forward. `days` must be more than 0 and a maximum of 365.
10. The answer gives the new day and the memories that arrived (`new_memories`).

### Events

11. `POST /api/events` tells the engine about an event. Use one of two forms.
12. **Preset form:** send `preset` (the name of an event in `poc/data/events.json`). You can also send `witnesses`. If you send no `witnesses`, the engine uses the preset's default witnesses.
13. **Full form:** send `type` (a short tag, for example `location_cleared`), `location` (a place or town), `facts` (each with `text` and `importance`) and `witnesses`.
14. If the request has no preset and does not have all of `type`, `location` and `facts`, the engine answers with `400`.
15. The answer gives the stored event and the memories that it made (`new_memories`).

### Conversation

16. `POST /api/dialog/open` with `npc_id` starts a conversation with a greeting. The answer is one turn (see `conversation.md` rule 27).
17. `POST /api/dialog/choose` with `npc_id`, `session_id` and `text` sends what the player says. The answer is the next turn.
18. `session_id` is the conversation number from the greeting turn.
19. `text` must have 1 to 500 characters. The engine removes spaces at the start and the end.

### Inspector

20. `GET /api/npc/{npc_id}/knowledge` shows all the memories of one NPC, the strongest first. It also shows the last 12 turns.
21. For each memory, the answer shows:
   - its strength, and if it is clear, vague or forgotten (`stage`);
   - the facts that it keeps (`kept`);
   - the facts that faded (`faded`);
   - the facts that gossip lost (`lost_in_retelling`).
22. `GET /api/npc/{npc_id}/prompt` shows the prompt that the NPC will get in the next turn. It does not call the AI model.

### Saves

23. `POST /api/saves` with an optional `label` makes a save. The answer gives the new save number and the list of all saves.
24. `POST /api/saves/{save_id}/load` loads a save. The answer gives the day of the save.
25. `POST /api/reset` resets the world. The answer gives the start day.

### Test page

26. `GET /` gives the test web page.

### Voice

27. `GET /api/audio/{turn_id}` gives the voice of the NPC's line in that turn. The sound arrives in parts, so it can start to play before it is complete.
28. The engine answers with `404` if the voice is off, if the turn is unknown, or if the NPC has no voice.
29. The engine makes the voice again for each request. It does not keep old sound files.
30. Each NPC has its own voice, from `voice_id` in the world file.

Examples:
- If a mod sends `POST /api/clock/advance` with `days` = `-2`, then the engine answers with `400`.
- If a mod sends `POST /api/dialog/open` for an NPC that is not in the world file, then the engine answers with `404`.
- If there is no `ELEVENLABS_API_KEY`, then `GET /api/audio/7` answers with `404`, and `/api/session/start` gives an empty `tts`.

## Constraints

- The API is for one computer only. It has no login.
- The engine handles one request at a time. Two mods at the same time wait for each other.

## Planned Changes

| Ticket | Summary |
|---|---|
| #8 | A route to add NPCs while the game runs. |
| #9 | `POST /api/clock/set`: set the clock from the game's time. |
| #10 | The voice goes into a sound file that the Cyberpunk mod can play, not only as a stream. |
| #11 | Saves and loads by a name that the game gives (`/api/saves/{token}/load`). |
