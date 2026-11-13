# Talk Mod (code map)

The redscript mod that builds `what/talk.md`. It runs in the game and talks to the engine only through the HTTP API.

## Module Map

| File | Key Symbols | Responsibility |
|---|---|---|
| `r6/scripts/genpc/System.reds` | `GenpcSystem`, `GenpcState`, `GenpcTick`, `GenpcTimeout`, `@wrapMethod(InteractionUIBase) OnDialogsData` | The whole flow: keys, checks, HTTP requests, voice, close, timeouts. Hides the game choices. |
| `r6/scripts/genpc/Panel.reds` | `GenpcPanel`, `GenpcTypePopup` | The HUD widgets (panel and hint) and the text box popup. |
| `r6/scripts/genpc/Npc.reds` | `GenpcNpc` | Static helpers: name, record ID, entity ID, gender, starter cast, story characters, town, checks. |
| `r6/scripts/genpc/Settings.reds` | `GenpcSettings`, `GenpcTalkKey` | The Mod Settings page: talk key and voice on or off. |
| `r6/scripts/genpc/World.reds` | `GenpcWorldJson()` | Generated. The text of `world.json`. |
| `r6/tweaks/genpc.yaml` | `Genpc.NoWeapons` | The mod's own weapon block (a copy of `GameplayRestriction.NoWeapons`). TweakXL loads it. |
| `r6/audioware/genpc/genpc.yml` | `genpc_voice_1` … `genpc_voice_4` | The Audioware manifest for the 4 slot files. |
| `tools/world_reds.py` | `render`, `main` | Writes `World.reds` from `world.json`. |
| `tests/test_mod_files.py` | | Offline checks of the mod files. |

## Data Flow

1. `Session/Ready` → `OnSessionReady`: builds the HUD widgets, starts the 0.25 s tick, `POST /api/session/start` → `OnLoadStart` → `POST /api/world` (rules 1, 1a).
2. `Input/Key` (release only) → `OnKey`. The talk key in `Idle` → `TryOpen`: look-at target, `Refusal` (rule 7), then `POST /api/session/start` with a 3 s `GenpcTimeout` (state `Checking`).
3. `OnTalkStart` → `OpenPanel` (state `Waiting`, weapons blocked, game choices hidden) → `POST /api/world` only if `world` is not `cyberpunk` → `SendNpc` → `POST /api/npcs` → `OnNpc` → `POST /api/dialog/open` → `OnLine` (state `Showing`).
4. `OnLine` → `AskVoice` → `POST /api/audio/{turn_id}/slot` → `OnVoice` → Audioware `RegisterEmitter` (once per NPC) and `PlayOnEmitter(slot)`.
5. Keys `1`–`3` → `Choose` → `Say` → `POST /api/dialog/choose` → `OnLine`. `Enter` → `StartTyping` (popup); `Enter` again → `SendTyped` → `Say`.
6. `OnTick` → `CloseReason` while the panel is open, `UpdateHint` while idle. `Close` undoes everything.

## Key Abstractions

- **Request numbers.** Each request of a conversation gets a new number from `Expect()`, kept in `pending`, and sent as `HttpCallback` data. `IsCurrent` accepts only the answer to `pending`, and only in the expected state. A timeout, `Close` and `ResetTalk` set `pending` to `-1`, so late lines are ignored (rules 25, 28a). The voice has its own number, `voiceId`; `Say` and `Close` clear it, so only the voice of the line on the panel plays.
- **One timeout at a time.** `StartTimeout` takes a new `timeoutToken` and cancels the old one. 3 s for the check, 60 s for each line. A timeout with an old token does nothing.
- **Nothing stays in a save.** `Session/BeforeSave` closes the panel. `Session/Ready` always removes `Genpc.NoWeapons`. The game choices come back only if the player closed the panel near the NPC (talk key, menu, pause, phone call); else the game makes new ones.
- **Menus.** A listener on `UI_System.IsInMenu` and `Session/Pause` close the panel, because the tick may not run in a menu. `OnKey` ignores keys while a menu is open.
- **One tick at a time.** `tickGen` goes up at each load. A tick with an old `gen` stops.
- **States.** `Idle` → `Checking` → `Waiting` ↔ `Showing`; `Stuck` after "No answer." or an error. `IsPanelOpen` is true for `Waiting`, `Showing` and `Stuck`.

## Integration Points

| Consumer | Provider | Mechanism |
|---|---|---|
| `GenpcSystem` | engine | RedHttpClient `AsyncHttpClient.PostJson` to `http://localhost:8000` |
| `GenpcSystem` | Audioware | `GetAudioSystemExt`, tag `n"genpc"` |
| `GenpcTypePopup` | Codeware | `InGamePopup`, `HubTextInput`, `CustomPopupManager` |
| `GenpcSettings` | Mod Settings | `@runtimeProperty("ModSettings.*")`, `RegisterListenerToClass` |
| `GenpcSystem` | game | `PreventionSystem` (district), `StatusEffectHelper` (`GameplayRestriction.NoWeapons`), `UIInteractions` blackboard, `UI_System.IsInMenu`, `GetPhoneManager` |

## Implementation Notes

- **Starter cast by name.** `GenpcNpc.CastId` maps the shown name to the world-file `id`, because the record IDs are not known yet (`what/world.md` rule 7). `SendNpc` logs the record ID and the entity ID (rule 14). When the IDs are known, put them in `world.json` and match by record ID.
- **Refusal reasons.** `RefusalWhy` gives a short code (`down`, `far`, `hostile`, `combat`, `vehicle`, `scene`, `dialogue`, `story`); `Refusal` turns it into the note of rule 7. `LogRefusal` logs the code once for each NPC that has no hint, except `far` and `down`.
- **Text keys.** A crowd NPC can give a text key such as `NCResident` instead of a name. Only for such a key (`IsKey`), `Name` asks `GetLocalizedTextByKey` for its text, because a lookup of a real name such as "Sandra Dorsett" gave "Stranger"; if there is none and `IsKey` says it is one word with a capital letter inside, the name is "Stranger" (rule 12a).
- **Story characters by name.** `IsStoryCharacter` compares English names. A game in another language shows other names. Record IDs will fix this too.
- **The callback signature.** With `HttpCallback.Create(this, fn, [ToVariant(id)])`, the callback must take `(response, data: array<Variant>)`. Without data, only `(response)` (spike README).
- **Text box.** `typing` becomes true only in the popup's `OnShown` (`OnTypingOpened`), so a popup that does not open cannot lock the keys. `HubTextInput` ignores `Enter`; `OnKey` catches it. The popup is modal, so the game keys stop while the player types. Its `SetTimeDilation` is empty, so the game does not slow down. `Esc` closes the popup (its `cancel` action); `OnHide` calls `OnTypingClosed`.
- **Sound sources.** Emitters are removed only at `Session/BeforeEnd`. Audioware removes them when an NPC dies.
- **Not verified in the game yet:** that `Genpc.NoWeapons` stops keys `1`–`3`; that `F` cannot pick a hidden game choice (a known risk); that `Input/Key` still fires while the popup is open; the district parent links; the gender value of `GetGender()`.
- **Compile check without the game.** See `spike/README.md`, "Compile without starting the game".
- **World file.** After a change of `world.json`, run `uv run python mods/cyberpunk/tools/world_reds.py`. A test fails if you forget.
