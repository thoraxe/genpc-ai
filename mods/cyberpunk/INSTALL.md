# Install the Cyberpunk 2077 mod

The mod needs three things:

1. **The engine**, running on your PC. Install it first: see [`INSTALL.md`](../../INSTALL.md) at the top of this repo.
2. **The modding tools** below. Other people make them. The mod is built on them.
3. **The mod's own files.**

Tested on 2026-11-10 with Cyberpunk 2077 **patch 2.5** (Steam, game version 3.0.88.46235). The mod does not need Phantom Liberty or any other paid content.

## Before you start

1. **Stop the game from updating by itself.** In Steam, right-click Cyberpunk 2077, choose **Properties**, then **Updates**, and set it to **"Only update this game when I launch it"**. A game patch can break the modding tools. When Steam offers an update, wait until every tool below says that it supports the new patch.
2. **Install the Visual C++ Redistributable 2022 (x64)** from https://aka.ms/vs/17/release/vc_redist.x64.exe. If it is already installed, choose **Repair**.
3. **Find the game folder.** For Steam it is usually `C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077`. In Steam, right-click the game, then **Manage**, then **Browse local files**.

## How to "extract into the game folder"

Each tool is a zip file. For each one:

1. Right-click the zip and choose **Extract All...**
2. As the destination, give the game folder.
3. If Windows asks to merge folders or replace files, say **Yes**. Allow administrator permission if Windows asks.

Afterwards, the zip's folders (`bin`, `engine`, `r6`, `red4ext`) are **inside** the game folder, next to the game's own folders. If you see a folder like `Cyberpunk 2077\RED4ext-1.31.0\red4ext`, it went one level too deep: move the inner folders up.

## 1. Install the modding tools

Download each zip from the link, and extract it into the game folder **in this order**. Use these exact versions. Do not take versions marked "rc", "beta" or "preview", except where the table says so.

| # | Tool | Version | Download | Why the mod needs it |
|---|------|---------|----------|----------------------|
| 1 | RED4ext | 1.31.0 | [red4ext-1.31.0.zip](https://github.com/wopss/RED4ext/releases/tag/v1.31.0) | Loads the other tools |
| 2 | redscript | 0.5.32 (**not** 1.0) | [redscript-v0.5.32-windows.zip](https://github.com/jac3km4/redscript/releases/tag/v0.5.32) | Builds the mod's scripts |
| 3 | Cyber Engine Tweaks (CET) | 1.38.1 | [cet_1_38_1.zip](https://github.com/maximegmd/CyberEngineTweaks/releases/tag/v1.38.1) | Shows the mod's log lines; other tools need it |
| 4 | ArchiveXL | 1.28.6 | [ArchiveXL-1.28.6.zip](https://github.com/psiberx/cp2077-archive-xl/releases/tag/v1.28.6) | Mod Settings needs it |
| 5 | TweakXL | 1.12.0 | [TweakXL-1.12.0.zip](https://github.com/psiberx/cp2077-tweak-xl/releases/tag/v1.12.0) | Audioware needs it |
| 6 | Codeware | 1.21.2 | [Codeware-1.21.2.zip](https://github.com/psiberx/cp2077-codeware/releases/tag/v1.21.2) | Key presses and the on-screen panel |
| 7 | RedData | 0.11.0 | [RedData-0.11.0.zip](https://github.com/rayshader/cp2077-red-data/releases/tag/v0.11.0) | Reads the engine's replies |
| 8 | RedFileSystem | 0.16.0 | [RedFileSystem-0.16.0.zip](https://github.com/rayshader/cp2077-red-filesystem/releases/tag/v0.16.0) | RedHttpClient keeps its settings with it |
| 9 | RedHttpClient | 0.8.0 (from GitHub, not Nexus) | [RedHttpClient-0.8.0.zip](https://github.com/rayshader/cp2077-red-httpclient/releases/tag/v0.8.0) | Talks to the engine |
| 10 | Audioware | 1.11.0 | [Audioware-windows-v1.11.0.zip](https://github.com/cyb3rpsych0s1s/audioware/releases/tag/v1.11.0) | Plays the NPC voices |
| 11 | Mod Settings | 0.2.29 | [mod_settings_v0.2.29.zip](https://github.com/jackhumbert/mod_settings/releases/tag/v0.2.29) | The mod's settings page |

Notes:
- **redscript:** take 0.5.32. Version 1.0 is new, and the other tools do not support it yet.
- **ArchiveXL, TweakXL:** take the zip without "pdb" in its name.
- **Audioware:** take the plain zip, not the `DEV_ONLY` or `PDB` one. Its log may say version 1.10.1. That is a known mistake in this release and is not a problem.
- **CET:** the first time the game starts, CET asks you to choose a key for its overlay. Choose a key you do not use in play, for example `~`.

Only for mod developers: [RedHotTools 1.3.0-beta.13](https://github.com/psiberx/cp2077-red-hot-tools/releases/tag/v1.3.0-beta.13) (`RedHotTools-1.3.0.zip`) reloads scripts without a game restart. Players do not need it.

## 2. Set the launch options

The engine runs on your own PC at `http://localhost:8000`. RedHttpClient normally refuses addresses like this. The `-no-tls` option allows them. It only allows addresses on your own PC or home network (`localhost`, `127.0.0.1` and `192.168.0.*`).

1. In Steam, right-click Cyberpunk 2077 and choose **Properties**.
2. On the **General** page, in **Launch Options**, type:
   ```
   --launcher-skip -skipStartScreen -no-tls
   ```
3. Close the window. Steam saves it at once.

`--launcher-skip` starts the game without the CD PROJEKT launcher. `-skipStartScreen` skips the "press any key" screen. `-no-tls` is the one the mod needs.

## 3. Install the mod's files

The mod is not released yet. Until it is, copy the `mods\cyberpunk\r6` folder from this repo into the game folder. Its files are:
- `r6\scripts\genpc\`: the scripts.
- `r6\tweaks\genpc.yaml`: the mod's weapon block while you talk.
- `r6\audioware\genpc\`: the sound list and its 4 slot files (`genpc_voice_1.mp3` to `genpc_voice_4.mp3`). Do not delete these sound files while the game runs: Audioware stops the game if a sound file is missing.

Then tell the engine where the slot files are. Add this line to the engine's `.env`, with your game folder:
```
AUDIO_SLOT_DIR=C:\Program Files (x86)\Steam\steamapps\common\Cyberpunk 2077\r6\audioware\genpc
```
The mod uses 4 slot files, so leave `AUDIO_SLOT_COUNT` out (the default is 4). Start the engine again after you change `.env`.

## How to talk

- Look at an NPC. If you can talk to them, the hint **[G] Talk** shows.
- Press **G**. The panel shows their line and 3 choices.
- Press **1**, **2** or **3** for a choice. Or press **Enter**, type, and press **Enter** again. **Esc** closes the text box.
- Press **G** again, or walk away, to close the panel.
- To change the key or turn the voice off: **Esc**, then **Mod Settings**, then **genpc**.

## What NPCs hear about

The mod tells the engine about your fights, your finished gigs and side jobs, and police chases with 2 stars or more. NPCs that saw it know at once. The rest of the district hears it 12 game hours later, and the next districts 24 game hours later if it is big news.

- Game time goes about 8 times faster than real time, so 12 game hours is about 1.5 hours of play. To see gossip sooner, sleep or wait in the game.
- Each event shows in the game log, with lines that start with `[genpc] event`.
- To turn it off: **Mod Settings**, then **genpc**, then **Send game events**.

## 4. Check that everything loaded

1. Start the engine (see [`INSTALL.md`](../../INSTALL.md)).
2. Start the game from Steam. Load a save, or start a new game, and play for a minute.
3. Press **Esc**. The pause menu has a **Mod Settings** entry.
4. Quit the game, and open these files in the game folder with Notepad. Each start makes new log files with the date in the name. To find the newest one, sort the folder by **Date modified**.

| Tool | File | Good |
|------|------|------|
| RED4ext | `red4ext\logs\red4ext-<date>.log` (the newest) | `8 plugin(s) loaded` (9 with RedHotTools), and no `error` lines |
| redscript | `r6\logs\redscript_rCURRENT.log` | Has the line `Compilation complete` |
| CET | `bin\x64\plugins\cyber_engine_tweaks\cyber_engine_tweaks.log` | `CET version v1.38.1` and no errors |
| RedHttpClient | `red4ext\logs\redhttpclient-<date>.log` | `TLS is disabled` (this shows that `-no-tls` works) |
| Audioware | `red4ext\logs\audioware-<date>.log` | `no error reported!` |
| Mod Settings, RedFileSystem | `red4ext\logs\mod_settings-<date>.log`, `red4ext\logs\redfilesystem-<date>.log` | No errors |
| ArchiveXL, TweakXL, Codeware | `red4ext\plugins\<tool>\<tool>-<date>.log` | No errors |

The mod's own log lines start with `[genpc]`. To see them while you play, open the CET overlay and look in its **Game Log** window.

## If something is wrong

- **The game shows a message that script compilation failed.** Read `r6\logs\redscript_rCURRENT.log`. The message names the mod that caused it. When one script mod fails, the game loads **no** script mods, so other mods can seem broken too.
- **The mod says there is no reply from the engine.** Check that the engine window is open and shows `Uvicorn running`. Check that the launch options have `-no-tls`. Then read the newest `red4ext\logs\redhttpclient-<date>.log`: it lists each request and each reply.
- **A tool is missing from the RED4ext log.** Its folder probably went one level too deep. See 'How to "extract into the game folder"' above.
- **The game was updated.** Check each tool's download page for a version that supports the new patch before you play.

## Remove the mod

- Delete the mod's folders `r6\scripts\<mod name>\` and `r6\audioware\<mod name>\`.
- Remove `-no-tls` from the launch options.
- To remove all the tools as well, delete the folders `red4ext`, `r6\scripts`, `r6\audioware` and `bin\x64\plugins`, and the files `bin\x64\winmm.dll`, `bin\x64\version.dll` and `bin\x64\global.ini`. Then use Steam's **Verify integrity of game files** to repair anything else.
  - **This also removes every other script mod you have**, because they use the same folders.
  - Some small files from the tools stay behind, for example in `r6\config` and `r6\cache`. They do no harm.
