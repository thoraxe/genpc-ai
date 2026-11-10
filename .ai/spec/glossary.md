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
| **world-file NPC** | An NPC that the world file describes. It has a hand-written description, and it can have a voice. | cast NPC | `world.npcs`, `kind` = `world` |
| **added NPC** | An NPC that the mod adds while the game runs. The world file does not have it. A named NPC or a crowd NPC. | registered NPC, dynamic NPC | `kind` = `named` or `crowd` |
| **named NPC** | An added NPC with a record ID. It remembers the player, like a world-file NPC. | unique NPC | `kind` = `named` |
| **crowd NPC** | An added NPC with only an entity ID. It keeps no facts from the player after a conversation. | generic NPC, random NPC | `kind` = `crowd` |
| **record ID** | The fixed name of a character in the game data, for example `Character.wilson`. It does not change between games or loads. | TweakDB ID (in what/ files) | `record_id` |
| **entity ID** | A number that the game gives to a crowd NPC. It is good only until the next load. | hash, entity hash | `entity_id` |
| **faction** | A group that an NPC belongs to, for example a gang or a company. | gang, affiliation | `faction` |
| **general description** | The description that each added NPC gets. It comes from the world file. | generic bio, default bio | `generic_bio` |
| **voice list** | A list of voices in the world file for added NPCs. It has voices for each gender. | voice pool | `voice_pool` |

## Knowledge

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **event** | A thing that happened in the game, for example "the player killed the bandits". | incident, happening | `WorldEvent` |
| **fact** | One short sentence about an event or about the player. Each fact has an importance. | detail, info | `Fact` |
| **importance** | A number from 1 to 5 for a fact. 5 is the most important. | priority, weight | `importance` |
| **witness** | An NPC who saw the event. | observer | `witnesses`, source `witnessed` |
| **gossip** | Facts that an NPC heard from other people, not saw. | rumor, hearsay, news, hop | source `hop1`, `hop2` |
| **memory** | All the facts that one NPC knows about one event, or about one conversation. | knowledge item, record | `Memory` |
| **strength** | A number that shows how well an NPC remembers a memory. It gets smaller as days pass. | salience (salience is only the start value) | `strength()` |
| **lost fact** | A fact of an event that gossip did not carry, because its importance was too low. The NPC never knew it. | dropped fact | `lost_in_retelling` (inspector only) |
| **faded fact** | A fact that a vague memory does not keep, because its importance is too low. | forgotten fact | `dropped_facts`, `faded` |
| **key word** | A word of 4 or more letters that is not a common word ("the", "about", "player" and others). The engine compares key words to check a fact. | term | `_terms`, `_STOP` |
| **clear** | A memory that the NPC remembers with all its facts. | detailed, sharp | stage `detailed` |
| **vague** | A memory that the NPC remembers only partly. The NPC keeps only the important facts. | gist, fuzzy | stage `gist` |
| **forgotten** | A memory that the NPC does not remember. It never goes to the AI model. | lost, deleted | stage `forgotten` |
| **recall** | One time that the engine gives a memory to the AI model in a delivered reply. Each recall makes the memory stronger. Only the first 2 recalls have an effect. | use, access | `recalls` |
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
| **load** | Use a save again. Everything after the save stops existing. | restore, revert | `Store.load` |
| **start day** | The day on the clock at the start, and after a reset. It is 41 now. | first day | `POC_START_DAY` |
| **reset** | Remove all events, memories and turns, and set the clock to the start day. Saves stay. | wipe, clear | `Store.reset` |

## Project

| Word | Meaning | Do not write | Code name |
|---|---|---|---|
| **engine** | The Python program in `poc/engine/`. It keeps the knowledge and talks to the AI model. | backend, server | `engine` |
| **mod** | A small program inside a game. It sends events to the engine and shows the NPC's line. | plugin, client (in what/ files) | — |
| **owner** | The person who decides what the product does. The owner reads specs, not code. | user, boss | — |
| **issue** | A page on GitHub for one goal or problem, with a number, for example #9. | ticket, task | — |
| **spec** | The rules for one change in behaviour, in plain English, with examples. | requirements, design | — |
| **spec PR** | A PR for one change in behaviour. First it has only the new rules (the spec stage). After the owner's OK, it also gets the code (the code stage). | spec comment, behaviour PR | `spec/` branch |
| **spec stage** | The first part of a spec PR. It has only the new rules and the Summary. It ends with the owner's OK. Not the same as the `stage` of a memory in the code. | draft | — |
| **code stage** | The second part of a spec PR. We add the code and the tests to the same PR. | build phase | — |
| **merge** | Put the changes of a PR into the project. | land, ship | — |
| **live eval** | A test that uses the real AI model many times. It counts how often NPCs say wrong things. | benchmark | `poc/scripts/eval.py` |
| **preset** | An event that is ready in a file, for tests and demos. | template, sample event | `poc/data/events.json` |
| **test page** | A simple web page for tests. It uses the HTTP API like a mod. | UI, web UI | `poc/ui/index.html` |
| **inspector** | The part of the test page (and its route) that shows all the memories of one NPC. | debugger | `/api/npc/{id}/knowledge` |
| **PR** | A "pull request": a set of changes that waits for review before it goes into the project. | merge request | — |
