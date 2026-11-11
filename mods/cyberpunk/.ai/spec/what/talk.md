# Talk to an NPC in the Game

The player looks at an NPC and presses a key. A panel opens on the screen. The panel shows the NPC's line, 3 choices and a box for typed text. The voice comes from the NPC. The engine rules for a conversation are in the engine spec (`.ai/spec/what/conversation.md` and `http-api.md`).

Words in this file:
- **talk key:** the key that opens and closes the talk panel.
- **talk panel:** the mod's panel on the screen for one conversation.
- **talk distance:** the maximum distance between the player and the NPC for a conversation.
- **story character:** an NPC of the game's main story or of a story mission. Example: Misty or Viktor.
- **game choices:** the choices that the game itself shows for an NPC. Example: "Trade" for a vendor.
- **game log:** the log of the game. The player sees it in the "Game Log" window of the Cyber Engine Tweaks overlay.
- **crowd mark:** the game's own mark on an NPC of the street crowd.

## Behavioral Rules

### Start

1. When a game loads, the mod sends `POST /api/session/start` (engine `http-api.md` rule 5). Then it sends the Cyberpunk world (`world.md` rule 12). [PLANNED: #12]
1a. It is safe to send the world again. The engine keeps the memories (engine `world-file.md` rules 16i and 16j). [PLANNED: #12]
2. Before each greeting, the mod sends `POST /api/session/start` again. The engine must answer in 3 seconds. [PLANNED: #12]
2a. If the engine's world is not `cyberpunk`, the mod sends the Cyberpunk world before the greeting. Example: the engine started again during play (engine `world-file.md` rule 16q). [PLANNED: #12]
3. If the engine does not answer in 3 seconds, the panel does not open. The mod shows a note (rule 7). [PLANNED: #12]
4. The mod writes the world, `audio_slots` and the AI model name from the answer to the game log. [PLANNED: #12]

### Open the talk panel

5. Look at an NPC and press the talk key. The talk panel opens when the player releases the key. [PLANNED: #12]
5a. The talk key is `G`. The player can change it in the settings (rule 30). (owner question 1) [PLANNED: #12]
5b. When the player looks at an NPC that can talk, the hint "[G] Talk" shows on the screen. It shows the key from the settings. (owner question 1) [PLANNED: #12]
5c. The talk key does not replace a game action. Example: `F` still opens "Trade" for a vendor. [PLANNED: #12]
5d. The hint does not show for a story character, a dead NPC or an NPC more than 4 metres away. [PLANNED: #12]
6. The NPC must be in talk distance: a maximum of 4 metres. Example: at 3 metres, the panel opens. At 6 metres, it does not open. [PLANNED: #12]
7. In these cases, the panel does not open. The mod shows a short note on the screen. [PLANNED: #12]

| Case | Note |
|---|---|
| The NPC is more than 4 metres away. | "Move closer." |
| The NPC is dead or unconscious. | (no note) |
| The NPC is hostile, or the player is in combat. | "Not now." |
| The player is in a vehicle. | "Not now." |
| The NPC is in a game conversation or a scene. | "Not now." |
| The NPC is a story character (rule 11). | "This person does not want to talk." |
| The engine does not answer in 3 seconds (rule 3). | "The engine does not run. Start it, then try again." |

8. If the player looks at a device, a car or nothing, the talk key does nothing. [PLANNED: #12]

### Which NPC the player talks to

9. An NPC of the starter cast (`world.md` rule 6) is a world-file NPC. It uses its own description and voice. It remembers the player. [PLANNED: #12]
10. The mod sends `POST /api/npcs` before each greeting (engine `http-api.md` rule 31). The table shows what the mod sends. [PLANNED: #12]

| NPC in the game | What the mod sends | Kind (in the engine's answer) | Remembers the player |
|---|---|---|---|
| An NPC of the starter cast | `record_id` = the NPC's `id` in the world file | `world` | yes |
| An NPC without the crowd mark, for example a vendor | `record_id` = the game's record ID | `named` | yes |
| An NPC with the crowd mark | `entity_id` = the game's entity ID | `crowd` | no |

10a. A crowd NPC can get the entity ID of an earlier crowd NPC after a load. Then it gets the name, gender and voice of the earlier NPC. This does no harm: a crowd NPC keeps no facts from the player. [PLANNED: #12]
11. The mod has a fixed list of story characters. The player cannot talk to them. (owner question 2) [PLANNED: #12]
12. The mod sends the name that the game shows for the NPC. It also sends the NPC's gender, if the game gives it. [PLANNED: #12]
12a. If the game shows no name, the mod sends `Stranger`. [PLANNED: #12]
12b. If the name has more than 60 characters, the mod sends only the first 60 characters. [PLANNED: #12]
13. The mod sends the town where the player is. The game gives the district. The district is the town (`world.md` rules 2 and 5). [PLANNED: #12]
13a. Each area of the Badlands is the town Badlands. [PLANNED: #12]
13b. After each load, the mod uses Watson until the game gives a district. [PLANNED: #12]
14. The mod writes the record ID or the entity ID of the NPC to the game log. Thus we can find the record IDs of the starter cast (`world.md` rule 7). [PLANNED: #12]

### Talk

15. After the engine answered (rule 2), the panel opens. It shows the NPC's name and "…" until the greeting arrives. [PLANNED: #12]
16. When the greeting arrives, the panel shows the line, the 3 choices and the text box. [PLANNED: #12]
17. The mod then asks the engine for the voice (engine `http-api.md` rule 30a). It plays the voice from the NPC. [PLANNED: #12]
17a. The mod asks for no voice if the voice setting is off (rule 30), or if `audio_slots` is `0`. [PLANNED: #12]
17b. The mod tells the sound tool 4 slot names: `genpc_voice_1` to `genpc_voice_4`. If `audio_slots` is not `4`, the mod plays no voice and writes a line to the game log. [PLANNED: #12]
17c. The mod plays the slot that the engine's answer names. [PLANNED: #12]
18. The line does not wait for the voice. Example: the line shows after 3 seconds, and the voice starts about 1 second later. [PLANNED: #12]
19. Press `1`, `2` or `3` to pick a choice. The mod sends the text of that choice. [PLANNED: #12]
19a. While the panel is open, the game does not get `1`, `2` and `3`. Thus the player does not take out a weapon. [PLANNED: #12]
19b. After any choice, the panel stays open. This is also true for the choice to leave. The player closes the panel (rule 24). [PLANNED: #12]
20. Press `Enter` to type. Press `Enter` again to send the text. [PLANNED: #12]
20a. While the player types, all keys go into the text box. The game's keys and the talk key do nothing. Example: `G` types a "g". [PLANNED: #12]
20b. If the text is empty or only spaces when the player presses `Enter`, the mod sends nothing. The text box closes. [PLANNED: #12]
20c. The text box takes a maximum of 500 characters (engine `http-api.md` rule 19). Example: the 501st letter does not appear. [PLANNED: #12]
21. After the player sends, the panel shows "…" until the next line arrives. The player cannot send again during this time. [PLANNED: #12]
22. The game does not stop while the engine works. If the player does not type, the player can move and look around. (owner question 3) [PLANNED: #12]
23. While the panel is open, the game choices of that NPC are hidden. They come back when the panel closes. [PLANNED: #12]

### Close the talk panel

24. The panel closes in these cases: [PLANNED: #12]
   - The player presses the talk key again, when the player does not type.
   - The player is more than 8 metres from the NPC. Example: at 9 metres, the panel closes. At 7 metres, it stays open.
   - Combat starts, or the NPC becomes hostile.
   - The NPC dies or becomes unconscious.
   - The player gets into a vehicle.
   - The game opens a menu, for example the pause menu with `Escape`.
   - A phone call starts.
   - The game loads a save.
25. If a line arrives after the panel closed, the mod does not show it and does not play its voice. [PLANNED: #12]
26. A voice that plays when the panel closes plays until its end. [PLANNED: #12]
27. The next talk key press starts a new conversation with a new greeting. [PLANNED: #12]

### Errors

28. If the engine does not answer a line in 60 seconds, the panel shows "No answer." The player closes the panel with the talk key. [PLANNED: #12]
28a. If the line arrives after "No answer.", the mod does not show it. [PLANNED: #12]
28b. If the engine answers with an error, the panel shows "The engine had a problem (code N)." Example: code `404`. [PLANNED: #12]
29. If the voice fails, the mod shows the line without the voice. [PLANNED: #12]

### Settings

30. The mod settings menu has two settings for this mod: (owner question 4) [PLANNED: #12]
   - the talk key (default `G`);
   - the voice on or off (default on).

### Game log

31. The mod writes a `[genpc]` line to the game log for each request to the engine, each answer code and each error. [PLANNED: #12]
32. The game log never shows a value from `.env`. The mod does not read `.env`. [PLANNED: #12]

## Constraints

- The game never waits for the engine. Each request runs in the background.
- The mod talks to the engine only through the HTTP API at `http://localhost:8000`.
- The mod changes no game save file.
- The settings need the separate "Mod Settings" mod (`mods/cyberpunk/INSTALL.md`).
- Dogtown needs Phantom Liberty. The mod does not support it (`world.md` rule 4).

## Planned Changes

| Ticket | Summary |
|---|---|
| #12 | Talk to an NPC in the game: talk key, talk panel, voice from the NPC. |
