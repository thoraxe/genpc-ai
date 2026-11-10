# Constraints

These rules apply to the full project. Rules for one part are in that part's `what/` file. Build, test and Git rules are in `CLAUDE.md`.

1. The engine code contains nothing for one specific game. Towns, places, NPCs and the setting text go in the world file. Game actions go in the mod.
2. The prompt contains only facts that the engine chose for that NPC. It never contains the world state or the memories of other NPCs.
3. The knowledge rules are fixed. They never use the AI model, chance or the real clock. You can change their numbers in the `rules` part of the world file.
4. Secret keys are only in the `.env` file. Never show a key in code, logs, tests, PR text or error messages.
5. Each bug fix adds a test that fails before the fix and passes after it.
6. The owner approves behaviour, not code. Before you change what an NPC, a mod or a player sees, write a plain-language spec. Get the owner's OK first. Follow the "Writing rules for what/" in `README.md`.
7. Do not build lip sync, speech input or local AI models now. Do not use paid Cyberpunk content. Do not publish to Nexus without the owner's OK.
