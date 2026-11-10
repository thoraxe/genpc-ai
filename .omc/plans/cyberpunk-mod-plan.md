# Cyberpunk 2077 mod: plan

**Status:** pending approval · written 2026-11-10 · branch to use: `cyberpunk-mod` (off `poc-python-ui`)

## Goal
The player looks at an NPC in Cyberpunk 2077 (PC, patch 2.5), presses a key, and talks to them through our engine:
- the NPC's line appears as a subtitle and is spoken from the NPC;
- the player picks one of 3 choices or types free text.

What each NPC knows comes from our deterministic knowledge model:
- events happen in the game;
- gossip spreads between districts;
- memories fade with game time;
- loading a save rolls it all back.

No lip sync. Free to download, with no paywall (see `docs/monetization.md`).

## How it fits together
```
Cyberpunk (redscript mod)                        Python engine (existing PoC, generalised)
  key on looked-at NPC  ── POST /api/dialog/open ──▶  retrieve facts → LLM → validate
  ink panel: subtitle,  ◀── {npc_line, choices} ───   TTS → writes MP3 into an Audioware slot file
  3 choices, text box   ── POST /api/dialog/choose ─▶
  Audioware plays slot file on the NPC's emitter
  hooks: kill, quest, district, time ── POST /api/events, /api/clock/set
  save/load hooks ── POST /api/saves, /api/saves/{token}/load
```

## Mod stack
Researched 2026-11-10; sources are at the end.

| Need | Choice | Notes |
|---|---|---|
| Base | RED4ext, redscript, Codeware | Everything targets 2.5. Pin the versions and turn off game auto-update. |
| HTTP to localhost | **RedHttpClient 0.8** (MIT) + RedData (JSON) | `AsyncHttpClient` with a callback, so the game never freezes. HTTPS only by default: launch the game with `-no-tls`. Take the GitHub build, because the Nexus copy is older. |
| Dialog UI | Codeware ink HUD panel + `HubTextInput` | Hide the native choice hub while talking. Open on key *release*, so the key doesn't land in the text box. |
| Voice | **Audioware** `on-demand` slot files + `PlayOnEmitter(entityID)` | Audioware can't load files it doesn't know about at build time. So the engine overwrites a few pre-declared slot files, and the sound comes from the NPC. This means no streaming: the full MP3 is written first, adding about 0.5–1 s. |
| Who am I talking to | `TargetingSystem.GetLookAtObject` | Named characters: TweakDB record ID (stable). Crowd NPCs: per-session entity hash, with no lasting memory. |
| Settings | Mod Settings | Engine URL, talk key, voice on/off. |
| Dev loop | RedHotTools for script hot reload; `FTLog` for logs | I read the logs from the game folder. |

**Reference mod:** *Real Talk* (swillunderscore, GitHub) does almost exactly this stack. It has **no licence**, so we may study it but not copy code. RedHttpClient is MIT. Audioware is a runtime dependency only.

## Milestones
Each one ends with a check you can see in-game.

**C0: Spike: prove each risky piece in isolation** (about 1 session; needs you at the game)
1. You install the frameworks and pin the versions. I write the install list and the exact versions.
2. Hello-world redscript: press a key and see a log line plus a HUD text.
3. RedHttpClient async GET to `http://localhost:8000/api/world` with `-no-tls` shows the day on screen. **This is the biggest unknown.**
4. Audioware plays a pre-made MP3 slot file on a looked-at NPC. Then overwrite the file and play it again: do we hear the new audio?

*Gate:* if HTTP or slot-file overwrite fails, stop and choose a fallback before building more. Fallbacks:
- HTTP: file IPC, which another open mod uses.
- Audio: play outside the game through the engine's speakers. It isn't positional, but it works.

**C1: Make the engine game-neutral** (I do this alone; offline tests)
- **World file declares the setting.** `world.json` holds the setting text that's now hard-coded in `dialog.py:87` ("medieval fantasy village"). Add `world.cyberpunk.json`:
  - districts as "settlements" with adjacency (Watson, Westbrook, City Center, Heywood, Santo Domingo, Pacifica, Dogtown, Badlands);
  - a starter cast.
- **Unknown NPCs get created on the fly** from what the game sends (name, record ID, faction, district) with a generic bio. Named NPCs from the cast file keep their hand-written bio and voice.
- **The clock follows the game:** `POST /api/clock/set` with the game's hours. It still only moves forward. A backwards jump means a load, which the save binding handles.
- **Audio goes to a file:** when the mod asks, the engine writes the MP3 for a turn into a configured Audioware slot folder and returns the slot name.
- **Saves are keyed by a token the game sends**, instead of by our own integer IDs.
- All of it is covered by new tests. The browser test page keeps working.

**C2: Talk in-game**
- Look at an NPC and press the key to open the panel. The opening line is shown and spoken, with 3 choices plus a text box. Leaving closes it.
- *Pass:* 5 conversations with 3 different named NPCs, with no freeze while the LLM thinks and no stuck input.

**C3: The world feeds the engine**
- Hooks that POST events:
  - an NPC killed by the player, with where it happened;
  - quest or gig completed (Journal callback);
  - police heat changes;
  - the player entering a district (polled).
- Game time syncs on a timer and on load.
- *Pass:* a scenario like the Skyrim one.
  1. Clear a gig in Watson.
  2. A named NPC in Watson brings it up.
  3. One in Westbrook has only the vague version a day later.
  4. Someone in Pacifica knows nothing.

**C4: Save binding**
- A `persistent` token field in a `ScriptableSystem`. On `Session/BeforeSave` the engine takes a snapshot under that token. On load, it restores it.
- *Pass:*
  1. Talk to someone, then save.
  2. Talk again and tell them something new.
  3. Load the save: they don't know the new thing.
  4. Load an older save: they don't know any of it.

**C5: Hand to your tester**
- **Install doc:** frameworks, versions, the `-no-tls` launch option, how to start the engine, and which `.env` keys are needed.
- A one-click engine launcher (`.bat`).
- A zip containing `r6/scripts/...` and the Audioware manifest.
- I don't publish anything to Nexus without asking you.

## What I need from you
1. **Cyberpunk on this PC?** I need the install path, so I can compile-check scripts and read logs.
2. **Who are the NPCs?** Which ones does your tester care about: story characters (Misty, Viktor), regular vendors and fixers, random crowd NPCs, or characters from another mod?
3. **You at the keyboard for in-game checks.** I can't run the game. Each milestone ends with a short checklist for you to run, and I read the logs afterwards.
4. **Voices:** assign ElevenLabs voices per named NPC. Crowd NPCs get a pool by gender. ElevenLabs costs grow with how much your tester talks.

## Risks
| Risk | Effect | Mitigation |
|---|---|---|
| The `-no-tls` HTTP path doesn't work as described | No engine link | C0 spike first; file IPC as a fallback. |
| Overwriting a slot file doesn't replay new audio | No in-game voice | C0 spike; rotate between several slots; out-of-game audio as a fallback. |
| A game patch breaks the frameworks | Mod stops loading | Pin versions and document them; tell the tester to turn off auto-update. |
| Total delay is 3–5 s: LLM plus full TTS before playback | Feels slow | Show the subtitle as soon as the text arrives, with voice following. Shorter lines. Splitting the call in two later if needed. |
| Crowd NPCs aren't stable | They can't remember the player | Intended: only named NPCs get lasting memory. |
| z.ai Coding Plan key terms | Not for a third-party tester | Your tester uses their own key, or we switch to a standard z.ai or other OpenAI-compatible key. |
| CDPR's position on paid mods | Legal | Free only, no CDPR assets. |

## Effort (rough)
- C0: 1 session with you.
- C1: 1 session, by me alone.
- C2: 1–2 sessions.
- C3: 1 session.
- C4: 1 session.
- C5: half a session.

Most of the real time is the in-game test round-trips.

## Sources
- https://github.com/rayshader/cp2077-red-httpclient (v0.8.0, 2026-10-23; v0.7.1 `-no-tls`)
- https://github.com/cyb3rpsych0s1s/audioware (book: MANIFEST.md, SETTINGS.md)
- https://github.com/swillunderscore/realtalk (Identity, Target, UI, Input, Voice, Persona and Story `.reds`)
- https://github.com/ashcrowsz/ai-npc-cyberpunk-mod (file IPC, version pins)
- https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators/modding-tools/redhottools/rht-hot-reload
