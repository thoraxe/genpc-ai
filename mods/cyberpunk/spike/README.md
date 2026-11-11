# C0 spike: the mod tools work together

A small throwaway mod that proved the risky parts of the Cyberpunk mod (issues #3, #4, #5). It is not the real mod. Keep it as a working example.

Tested on 2026-11-11 with game patch 2.5 and the tools in [`../INSTALL.md`](../INSTALL.md).

## What it does

- **F7:** writes a `[genpc]` log line and shows text on screen (#3). Then it asks the engine for `GET /api/world` and shows the world and the day (#4).
- **F8:** plays the sound `genpc_slot_0` on the NPC you look at (#5).

## Results

| Test | Result |
|------|--------|
| #3 Key, log line, on-screen text | Pass. The log line shows in the CET overlay's **Game Log** window. It reaches `scripting.log` only later, so read the overlay while you play. |
| #4 HTTP to the engine | Pass. The reply came back in about 5 ms. No freeze was noticed. The `-no-tls` launch option set in Steam works (RedHttpClient's log says `TLS is disabled`). |
| #5 Overwrite a sound file, play again | Pass. After the file was overwritten while the game ran, the next play gave the new sound. The sound comes from the NPC's position: it moves between the left and right speakers when the player turns. |

So the plan works as written: the engine writes each line into a sound slot file, and the mod plays that slot on the NPC. No fallback is needed.

## Install

Copy the `r6` folder into the game folder. To use the test, start the engine first.

## Lessons for the real mod

- **RedHttpClient callback:** with no extra data, the function takes only the response: `cb func OnX(response: ref<HttpResponse>)`. With a second `data` parameter (and no data given to `HttpCallback.Create`), it is never called, and there is no error.
- **Imports:** `import RedHttpClient.*`, `import RedData.Json.*` and `import Audioware.*` are needed.
- **Key presses:** Codeware's `GameInstance.GetCallbackSystem().RegisterCallback(n"Input/Key", this, n"OnKey")` in a `ScriptableSystem`, and a check on `KeyInputEvent.GetKey()` and `GetAction()`. No input XML file is needed.
- **Audioware:** `RegisterEmitter(entityID, tag)` once, then `PlayOnEmitter(eventName, entityID, tag)`. The manifest sets `usage: on-demand` for each slot. Check that the target is an `NPCPuppet` (the look-at target can also be a device or a car), and stop if `RegisterEmitter` returns false.
- **Clean up:** the spike never unregisters its key callback or its emitters. The real mod must unregister them in `OnDetach`, and call `UnregisterEmitter` when an NPC goes away.
- **Compile without starting the game.** This shows script errors in seconds. Run it in the game folder:
  ```
  engine\tools\scc.exe -compile "<game>\r6\scripts" -customCacheDir "<game>\r6\cache" -compilePathsFile paths.txt -outputCacheFile out.redscripts
  ```
  `paths.txt` lists the plugin script folders with full paths, one on each line:
  ```
  <game>\red4ext\plugins\Codeware\Scripts
  <game>\red4ext\plugins\TweakXL\Scripts
  <game>\red4ext\plugins\ArchiveXL\Scripts
  <game>\red4ext\plugins\mod_settings
  ```
  The compiled scripts go to `out.redscripts`, not to the game's cache, so the game is not changed. The result is in `r6\logs\redscript_rCURRENT.log`. On a failure, scc also shows a popup.
