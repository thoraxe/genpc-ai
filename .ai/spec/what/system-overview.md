# System Overview

The engine gives AI characters (NPCs) in a game a memory that is logical. Each NPC knows only what it saw, or what it heard as gossip. Gossip arrives late and loses facts. Memories fade as days pass in the game. If the player loads a save, every NPC forgets what happened after that save. An AI model writes the words that an NPC says. The AI model gets only the facts that the NPC knows. Thus the NPC cannot tell a secret that it does not know.

See `glossary.md` for the meaning of each word.

## Behavioral Rules

### What the engine does

1. The engine decides what each NPC knows. The AI model does not decide this.
2. The engine uses fixed rules to decide what an NPC knows. The same events, days and conversations always give the same knowledge.
3. The AI model writes the NPC's line and 3 choices for the player. It also suggests facts about the player. The engine checks these facts.
4. The engine sends the AI model only the facts of the NPC that talks. It never sends facts that only other NPCs know.
5. The engine does not contain rules for one specific game. Each game gets a world file and a mod.

### The parts

6. **Knowledge** decides who knows which facts, and how memories fade. See `knowledge.md`.
7. **Conversation** makes each turn: it gets the NPC's facts, asks the AI model, and checks the reply. See `conversation.md`.
8. **Saves and clock** keep the day in the game, and save and load all knowledge. See `saves-and-clock.md`.
9. **HTTP API** is how a mod talks to the engine. See `http-api.md`.
10. **World file** describes the towns, places and NPCs of one game. See `world-file.md`.
11. **Voice** changes an NPC's line into sound. It is optional. See `http-api.md` rules 27–30.

### The full path of one event

12. The mod tells the engine about an event. The witnesses know all its facts immediately.
13. The mod tells the engine that days pass. Gossip then goes to more NPCs, with fewer facts.
14. The player talks to an NPC. The engine sends that NPC's facts to the AI model.
15. The AI model writes a line. The engine checks it and sends it to the mod.
16. If the player tells the NPC about themself, the NPC remembers only facts that the player really said.

Example: the player kills the bandits at Embershard Mine on day 41. Hrolf sees it. Hrolf knows all 5 facts on day 41. Torvald lives in the same town. He knows 3 facts on day 41.5. Eirik lives in the next town. He knows 2 facts on day 44. Sabine lives far away. She never knows.

## Configuration Surface

You set these values in the `.env` file at the top of the repo. Secret keys go only in `.env`.

| Setting | What it does | Default |
|---|---|---|
| `ZAI_API_KEY` | The secret key for the default AI model service (z.ai). | — (necessary) |
| `LLM_API_KEY_ENV` | The name of the setting that holds the AI model key. Use it to change to a different service. | `ZAI_API_KEY` |
| `LLM_BASE_URL` | The address of the AI model service. You can use any service that works like OpenAI. | `https://api.z.ai/api/coding/paas/v4/` (or `ZAI_BASE_URL`) |
| `LLM_MODEL` | The name of the AI model. | `glm-5.3-flash` (or `ZAI_MODEL`) |
| `LLM_REASONING_EFFORT` | How much the AI model thinks before it replies. Empty means "do not send". | `low` |
| `ELEVENLABS_API_KEY` | The secret key for the voice service. Without it, NPCs have no voice. | — (optional) |
| `ELEVENLABS_MODEL` | The voice model. | `eleven_flash_v2_5` |
| `TTS_ENABLED` | Set to `0`, `false` or `no` to stop the voice. | `1` |
| `POC_START_DAY` | The start day of the test world, and of a mod world that gives no `start_day`. | `41` |
| `POC_VAR_DIR` | The folder for the databases. Each mod world has its own database file there. | `poc/var` |
| `POC_DB` | The database file of the test world. | `poc/var/poc.db` |

The world file can change the knowledge numbers (for example, how fast memories fade). See `world-file.md`.

## Constraints

- The engine runs on the same computer as the game. It is not a public internet service.
- The engine has one shared database. It makes changes to knowledge and conversations one at a time.
- The test web page uses only the HTTP API. It gets no special access.

## Planned Changes

| Ticket | Summary |
|---|---|
| #7 | A mod sends its own world to the engine. The first mod's world is in the mod's specs. |
| ~~#8~~ | A mod can add new NPCs while the game runs. |
| #9 | A mod can set the clock from the game's own day. |
| #10 | The engine writes each line's voice into a sound file that a game mod can play. |
| ~~#11~~ | Saves use a name that the game gives, so a game save and an engine save match. |
| #20 | The live eval must not count "I don't know about that" as a leak. |
