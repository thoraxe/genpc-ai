# Cyberpunk 2077 mod — Specifications

The Cyberpunk 2077 mod lets the player talk to NPCs in the game through the engine. These specs tell what the mod must do and what game content it gives to the engine. The plan is in `.omc/plans/cyberpunk-mod-plan.md`.

## Structure

The structure and the writing rules are the same as for the engine specs. See `.ai/spec/README.md` at the top of the repo, "Writing rules for what/" and "Conventions".

| Layer | Path | Purpose |
|---|---|---|
| **what/** | `mods/cyberpunk/.ai/spec/what/` | What the mod must do, and the game content that it sends to the engine. |
| **how/** | `mods/cyberpunk/.ai/spec/how/` | Where the mod's code and files are. |

Use the words in the engine glossary (`.ai/spec/glossary.md`).

## Scope

In scope:
- The Cyberpunk world that the mod sends to the engine: districts (towns), NPCs, setting text and knowledge settings.
- What the mod does in the game: talk key, subtitles, choices, voice, events, clock and saves.
- The install package for the tester.

Out of scope:
- The engine and the HTTP API. The engine specs (`.ai/spec/`) are authoritative for them.
- Paid content (Phantom Liberty).

## Authority

These specs are authoritative for the mod and its game content. For the engine and the HTTP API, the engine specs are authoritative. A rule here can refer to an engine rule, for example "`http-api.md` rule 16".

## Status

- `what/world.md`: the Cyberpunk world that the mod sends to the engine.
- `what/talk.md`: how the player talks to an NPC in the game.
- `what/events.md`: fights, jobs and police chases that the mod sends to the engine, and the clock. [PLANNED: #13]

- `how/talk-mod.md`: where the mod's code is.

The in-game tests #3 to #5 passed (`mods/cyberpunk/spike/`). The mod's code is in `mods/cyberpunk/r6/`.
