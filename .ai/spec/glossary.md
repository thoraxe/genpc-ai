# Glossary

Each word has one meaning. Use only these words for these things in `what/` files. The "Code name" column shows the name in the code, for agents.

## People and places

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **NPC** | A character in the game that the player can talk to. The player does not control it. | character, bot, agent | `NPC`, `npc_id` |
| **player** | The person who plays the game. | user, hero | `player` |
| **town** | A place where NPCs live. Gossip moves between towns. In Cyberpunk, a town is a district. | settlement, village, city | `Settlement` |
| **next town** | A town that the world file lists as a neighbour of a different town. | adjacent town, nearby town | `adjacent` |
| **place** | A location that is not a town, for example a mine. Each place belongs to one town. | site, area | `Location`, `near_settlement` |
| **world** | All the towns, places and NPCs of one game. | setting (when you mean the world) | `WorldConfig` |
| **world file** | The file that describes the world (`poc/data/world.json`). | config, map | `world.json` |
| **setting text** | A short text in the world file. It tells every NPC how to speak. | flavour, style | `setting` |

## Knowledge

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **event** | A thing that happened in the game, for example "the player killed the bandits". | incident, happening | `WorldEvent` |
| **fact** | One short sentence about an event or about the player. Each fact has an importance. | detail, info | `Fact` |
| **importance** | A number from 1 to 5 for a fact. 5 is the most important. | priority, weight | `importance` |
| **witness** | An NPC who saw the event. | observer | `witnesses`, source `witnessed` |
| **gossip** | Facts that an NPC heard from other people, not saw. | rumor, hearsay, news, hop | source `hop1`, `hop2` |
| **memory** | All the facts that one NPC knows about one event, or about one conversation. | knowledge item, record | `Memory` |
| **strength** | A number that shows how well an NPC remembers a memory. It gets smaller as days go by. | salience (salience is only the start value) | `strength()` |
| **clear** | A memory that the NPC remembers with all its facts. | detailed, sharp | stage `detailed` |
| **vague** | A memory that the NPC remembers only partly. The NPC keeps only the important facts. | gist, fuzzy | stage `gist` |
| **forgotten** | A memory that the NPC does not remember. It never goes to the AI model. | lost, deleted | stage `forgotten` |
| **recall** | One time that the engine gives a memory to the AI model in a delivered reply. Each recall makes a memory fade more slowly. | use, access | `recalls` |
| **recent news** | A memory of an event that the NPC got less than 3 days ago and did not tell the player yet. | fresh gossip | `news_window_days`, `mentioned` |
| **told** | The NPC said the recent news to the player. The engine checks the NPC's words to decide this. | mentioned, shared | `mentioned` |

## Conversation

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **conversation** | All the turns between the player and one NPC, from the greeting until the player leaves. | session, chat, dialog | `session_id` |
| **turn** | One reply from the NPC. It has the NPC's line and 3 choices. | message, exchange | `turn`, `TurnResult` |
| **line** | The words that the NPC says in one turn. | response, utterance | `npc_line` |
| **choice** | A short thing that the player can say next. Each turn has 3 choices. | option, answer | `choices` |
| **greeting** | The first turn. The player walks to the NPC and the NPC speaks first. | opening, hello | `open` |
| **AI model** | The external language model (LLM) that writes the NPC's line and choices. It does not decide what the NPC knows. | LLM (in what/ files), the AI, GPT | `LLMProvider` |
| **prompt** | The text that the engine sends to the AI model before a turn. | instructions, context | `build_system_prompt` |
| **fallback line** | A safe line that the engine uses if the AI model fails. | default reply, error line | `FALLBACK` |
| **voice** | The sound of the NPC's line. A voice service makes it from the text. | audio, TTS (in what/ files) | `tts`, `voice_id` |

## Time and saves

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **day** | One day in the game. Never a real day. Days can have parts: 41.5 is the middle of day 41. | date, time | `day` |
| **clock** | The current day in the game. | time, timer | `meta.day` |
| **save** | A copy of everything that NPCs know, at one moment. | snapshot, checkpoint | `saves` table |
| **load** | Put a save back. Everything after the save stops existing. | restore, revert | `Store.load` |
| **reset** | Remove all events, memories and turns, and set the clock to the start day. Saves stay. | wipe, clear | `Store.reset` |

## Project

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **engine** | The Python program in `poc/engine/`. It keeps the knowledge and talks to the AI model. | backend, server | `engine` |
| **mod** | A small program inside a game. It sends events to the engine and shows the NPC's line. | plugin, client (in what/ files) | — |
| **owner** | The person who decides what the product does. The owner reads specs, not code. | user, boss | — |
| **live eval** | A test that uses the real AI model many times. It counts how often NPCs say wrong things. | benchmark | `poc/scripts/eval.py` |
