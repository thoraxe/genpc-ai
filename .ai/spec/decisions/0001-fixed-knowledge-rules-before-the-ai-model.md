# 0001: Fixed rules decide what an NPC knows

**Status:** accepted
**Date:** 2026-11-07

## Context

Most AI NPC mods give every NPC the same AI model, and the AI model knows everything. Thus a farmer can know a secret from the other end of the world. The AI model also invents facts. We want each NPC to know only what it saw or heard.

## Decision

- Fixed rules in the engine decide what each NPC knows: witnesses, gossip, fading and saves.
- The engine sends the AI model only the facts of the NPC that talks.
- The AI model writes the line and the choices. It also suggests facts about the player.
- The engine checks every reply. It keeps a fact from the player only if the player really said it.

## Other options

- **Let the AI model decide what the NPC knows.** We did not choose this. The result changes each time, and we cannot test it.
- **Use the game side of Mantella or CHIM.** The owner did not choose this. We want our own small mod and our own API. We only read these projects for ideas.

## Results

- Easier: we can test knowledge with normal tests, without the AI model. An NPC cannot tell what the engine did not give it.
- Harder: the engine must get every important event from the mod. If the mod does not send an event, no NPC knows about it.
