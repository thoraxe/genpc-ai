# 0007: Mods live in this repo, each in its own folder

**Status:** accepted
**Date:** 2026-11-10

## Context

The first mod is for Cyberpunk 2077. Its content (districts, NPCs, events) started to appear in the engine's specs. The engine must not know about one game. We also had to choose: one repo for the engine and the mods, or one repo for each mod.

## Decision

- Each mod lives in this repo, in its own folder: `mods/<game>/`. The first is `mods/cyberpunk/`.
- Each mod has its own specs in `mods/<game>/.ai/spec/`. They use the same structure and the same writing rules as the engine specs.
- The game content of a mod is in the mod's specs and the mod's files. It is never in the engine specs or the engine code.
- A mod talks to the engine only through the HTTP API. It never uses engine code or engine files.

## Other options

- **One repo for each mod now.** We did not choose this now. The HTTP API still changes often. In one repo, one PR can change the engine and the mod together. The owner also has one place to look.
- **Game content in the engine specs.** We did not choose this. The engine must work for every game without changes.

## Results

- Easier: one PR can change the API and the mod together. The owner follows one repo.
- Easier: the rules above keep each mod separate. Thus we can move a mod to its own repo later.
- Harder: different licences for the engine and a mod are less clean in one repo.
- We move a mod to its own repo when one of these is true: it needs a different licence, it has its own release dates, or other people build mods.
