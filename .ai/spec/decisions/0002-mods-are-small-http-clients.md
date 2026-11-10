# 0002: Game mods are small HTTP clients

**Status:** accepted
**Date:** 2026-11-07

## Context

We want the engine to work with more than one game. The first games are Cyberpunk 2077 and Skyrim. Mod tools for each game are very different.

## Decision

- The engine is a separate program on the player's computer.
- Each game mod is small. It sends events, the clock and saves to the engine. It shows the NPC's line, the choices and the voice.
- The mod and the engine talk over a small HTTP API (see `what/http-api.md`).
- The test web page uses the same API, so we can test without a game.

## Other options

- **Put the engine inside each game mod.** We did not choose this. We would write the knowledge rules again for each game.
- **Talk through files, not HTTP.** We keep this as a fallback, if a game cannot send HTTP requests (see `.omc/plans/cyberpunk-mod-plan.md`, step C0).

## Results

- Easier: one engine for all games. We can test the engine alone.
- Harder: the player must start the engine before the game. The API is an agreement, so we cannot rename fields freely.
