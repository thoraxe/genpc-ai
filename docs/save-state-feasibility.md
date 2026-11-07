# Save-State Attachment Feasibility (2026-11-07)

**Verdict:**
- **Skyrim SE/AE:** feasible, with caveats.
- **Cyberpunk 2077:** a token-based design for now. Storing the snapshot in chunks as `array<Int32>` might work; needs a spike.
- **Fallout 4, NV, 3 and Oblivion (2006):** the same co-save design as Skyrim.
- **Starfield and Oblivion Remastered:** no co-save; a sidecar or token is required.

## Recommended design (Skyrim): co-save snapshot + lineage token + engine cache
1. **On save:** the SKSE plugin writes `META` (schema version, `lineage_id`, `save_seq`, `parent_seq`, content hash) and `SNAP` (a compressed engine snapshot) into the `.skse` co-save. The co-save is the source of truth, and it moves together with the `.ess`.
2. **Engine cache:** keyed by `(lineage_id, save_seq)`. It exists only for speed and is never the source of truth.
3. **On load:** the plugin reads `META`. It sends just the hash if the engine already has that snapshot cached, otherwise it sends `SNAP`. The engine replaces its working state, which discards any abandoned timeline.
4. **Size:** use a full compressed snapshot each save. Keeping it under about 1–2 MB is believed safe. Evidence is anecdotal only: a 9 MB JContainers co-save caused lag, while 504 KB was fine.

## APIs
- **Serialization:** `SKSE::GetSerializationInterface()`: `SetUniqueID`, `SetSaveCallback`, `SetLoadCallback`, `SetRevertCallback`, `WriteRecord`, `GetNextRecordInfo`, `ReadRecordData`, `ResolveFormID`.
- **Messaging:** `GetMessagingInterface()->RegisterListener` for `kSaveGame`, `kPreLoadGame`, `kPostLoadGame`, `kNewGame`, `kDeleteGame`.

## Timing and gotchas
- **Save:**
  - `kSaveGame` (carries the save name) fires, then the save callbacks run synchronously inside the save.
  - No blocking HTTP inside the save callback: prefetch the snapshot at `kSaveGame`.
- **Load:**
  - Order: `kPreLoadGame`, then the load callbacks, then `kPostLoadGame(success)`.
  - Unverified: when revert runs relative to `kPreLoadGame`.
- **New game:** revert runs, then `kNewGame`. Mint a new `lineage_id` at this point.
- **Delete:** `kDeleteGame` fires before files are removed. Prune the cache then.
- **Save names are not identities:** quicksaves and autosaves reuse them.
- **Risk:** cloud sync or save managers may copy only the `.ess`. If `META` is missing, fall back to the cache or to "memory unknown". Steam Cloud's handling of `.skse` is unverified.
- **Records lost if the plugin is absent:** records are dropped when the plugin isn't loaded. Version the schema from day one.
- **Papyrus options are not suitable for MB-scale data:**
  - script properties hold the token only;
  - StorageUtil and JDB live in the co-save but are slow;
  - JsonUtil and `JValue.writeToFile` write external files that don't travel with the save.

## Existing mods
- **Mantella:** memory lives in external files keyed by player name + an MCM World ID slider. Separate per character, but no rollback when an older save is loaded.
- **CHIM:** a Postgres database. On load it deletes events with `gamets >=` the loaded save's game time; "Dragon Break" snapshots the abandoned timeline.

## Cyberpunk 2077
- **redscript:** `persistent` fields on `ScriptableSystem` are saved with the game. All types are allowed **except** `String`, `Variant` and `ResRef` (per the redscript and Codeware wikis).
- **Correction (re-check, 2026-11-07):** earlier this file said "integer-only". In fact arrays and persisted class instances are allowed, so storing the snapshot in chunks as `array<Int32>` may work. Its capacity and performance are untested.
- **Approach:**
  - Default: persist the lineage token and keep the state outside the save. The save then isn't portable without the engine's files.
  - Spike: try a 1 MB `array<Int32>`.
- **Codeware save hooks:**
  - `Session/BeforeSave` blocks the save until the callback returns, which makes the token-plus-sidecar approach safe.
  - `ScriptableService` persistence is global, not per save.
- **Not found:** any blob persistence API in Codeware or a RED4ext plugin.

## Other games (verified 2026-11-07)
Marks: V = checked in source or headers · D = from docs · U = unverified.

| Game | Mechanism | Where | Fit for our snapshot | Version risk |
|---|---|---|---|---|
| Fallout 4 | F4SE `F4SESerializationInterface` (same shape as SKSE), messages PreLoad/PostLoad/PreSave/PostSave/DeleteGame/NewGame [V] | `.f4se` co-save | **Same design as Skyrim** | High: next-gen split F4SE into 0.6.x/0.7.x and plugins needed recompiling; the serialization API itself is unchanged |
| Fallout NV | xNVSE serialization v2 [V] | `.nvse` | Same design | Low |
| Fallout 3 | FOSE serialization [V] | `.fose` | Same design, no delete hook | Low |
| Oblivion (2006) | xOBSE serialization [V] | `.obse` | Same design | Low |
| Oblivion Remastered | **None**: OBSE64 has no serialization or save events [V] | n/a | Token or sidecar only, needing our own hooks | Very high |
| Starfield | **None public**: SFSE disabled its preliminary serialization API in 0.2.12; Pre/PostSave and Load messages pass the save name [V] | Sidecar keyed to the save name | Sidecar only | High |
| Baldur's Gate 3 | BG3SE `Ext.Vars.RegisterModVariable(..., {Persistent=true})` (PersistentVars is deprecated) [V] | Inside the save, as JSON | base64 blob; size limit unknown; mark it server-only so it isn't synced | Medium |
| Bannerlord | `CampaignBehaviorBase.SyncData(IDataStore)`; ButterLib `SyncDataAsJson` [D] | Inside the save | String blob; size untested | Medium |
| RimWorld | `GameComponent.ExposeData` + `Scribe_Values` [D] | Inside the `.rws` save (XML) | base64 blob; adds about 1.35× size to the XML | Low to medium |
| Stardew Valley | SMAPI `Helper.Data.WriteSaveData` [V] | Inside the save (`CustomData`) | JSON or base64; host only in multiplayer | Low |
| Minecraft Java | `SavedData` / `PersistentState` [D] | `<world>/data/*.dat` | Works, but worlds save continuously, so "load an older save" means restoring a backup | High |

## Main-story characters (future; not in v1)
- **Leave vanilla quest dialogue alone.** Add an extra topic with conditions that opens generated conversation. The LLM never replaces a line a quest depends on.
- **Quest progress becomes engine facts.** An SKSE `TESQuestStageEvent` sink turns stage changes into WorldEvents.
- **Each NPC gets `tier: casual | key`.** For key characters:
  - the personality is locked;
  - facts are gated by quest stage and rebuilt from the save's quest stages on load.
- **Spoiler guard:** a strict instruction to use only the supplied facts, plus a check that blocks quest-related names the NPC hasn't learned yet. The risk is the LLM's own knowledge of Skyrim's plot.
- **Voices:** don't clone unique voice actors. Use text-only lines or licensed/synthetic voices.
- **Never** let the LLM change quest state.

## Third-party content packs (future)
- **What a pack declares:**
  - NPCs with `tier: key`, a personality and a voice;
  - knowledge gated by the pack's own quest stages;
  - its own event types (`pack:event`);
  - optional rules for how its rumors spread;
  - a policy for how much the LLM may generate.
- **Skyrim:** an optional dependency through native Papyrus functions and SKSE ModEvents (`NKE_IsAvailable`, `NKE_ReportEvent`, `NKE_SetFact`).
- **Cyberpunk:** quest mods exist, for example Deceptious Quest Core (Nexus 7831) and Night City Interactions. They need ArchiveXL and track state in FactsDB.
  - FactsDB is global, so we can read another mod's facts (`GetQuestsSystem():GetFact`) with no code from that mod's author, given the fact names.
  - Facts are Int32 only.
- **IDs and storage:** every ID is namespaced by its plugin. Each pack gets its own section of the co-save.
- **Removed plugins:**
  - When a pack's ESP has been removed, `ResolveFormID` returns false, and the plugin must discard that pack's state.
  - SKSE never drops records on its own. If our DLL is missing, its records are lost the next time the player saves over that file.
- **Packs only add to state.** They can't overwrite another pack's or the game's characters.

## Open re-checks
- Cyberpunk: capacity of a persistent array.
- BG3: ModVars at 1–2 MB.
- Bannerlord and RimWorld: performance with large blobs.
- Skyrim: a named quest mod with a documented integration API (not yet confirmed).

## Sources
https://raw.githubusercontent.com/ianpatt/skse64/master/skse64/PluginAPI.h · https://raw.githubusercontent.com/ianpatt/skse64/master/skse64/Hooks_SaveLoad.cpp · https://raw.githubusercontent.com/CharmedBaryon/CommonLibSSE-NG/main/include/SKSE/Interfaces.h · https://forums.nexusmods.com/topic/6985406-skse64-co-saves-comparative-size · https://github.com/ryobg/JContainers · https://wiki.redmodding.org/redscript/references-and-examples/common-patterns/persistence
