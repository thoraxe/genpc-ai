# Conversation

A conversation is the talk between the player and one NPC. Each turn, the engine gets the NPC's memories, writes a prompt, asks the AI model, checks the reply, and stores the result.

## Behavioral Rules

### Start and turns

1. A conversation starts with a greeting. The player walks to the NPC, and the NPC speaks first.
2. After the greeting, the player says something. The player can use one of the 3 choices or type free text.
3. The engine gives each conversation a number. The mod sends this number with each later turn.
4. The AI model sees the earlier turns of this conversation only. It does not see earlier conversations as turns.
4a. The engine looks at only the last 20 turns of the NPC. In a very long conversation, the AI model does not see the oldest turns.
5. An NPC knows about earlier conversations only through memories of facts from the player (see `knowledge.md` rules 29–33).

### What the prompt contains

6. The prompt contains only these things:
   - the NPC's name, job, town and description (from the world file);
   - the day in the game;
   - the setting text from the world file;
   - the memories that the engine chose for this NPC (see `knowledge.md` rules 24–28);
   - the rules for the AI model (rules 10–14a below);
   - the format of the reply.
7. The prompt never contains facts that only other NPCs know. It never contains facts that the NPC lost or forgot.
8. For each memory, the prompt tells how the NPC knows it and how old it is:
   - witness: "you saw this yourself";
   - same-town gossip: "you heard this from someone in town";
   - next-town gossip: "a rumor travelers brought from nearby";
   - a fact from the player: "the player told you this".
   - Age: "today" if it is less than 1 day old, else "about N days ago".
9. If the NPC has no memories, the prompt says that the NPC knows nothing special beyond normal life in the town.

### What the prompt tells the AI model

10. Talk only about the events in the list. Do not invent news, events, quests, names or places.
11. If the player asks about something that is not in the list, say in character that you do not know.
12. Gossip and vague memories must sound unsure ("they say", "I heard"). Do not add facts.
13. Say recent news without a request from the player, if you did not tell it yet.
14. The line is 1 or 2 short spoken sentences. It has no stage directions. Give exactly 3 choices of less than 12 words. One choice lets the player leave.
14a. List the facts that the player told about themself in their last line. Give each fact an importance from 1 to 5. If there are none, give an empty list.

### The reply from the AI model

15. The engine does not trust the reply. It checks the format of each reply.
16. A good reply has a line of 1 to 600 characters and 3 or more choices.
16a. A reply can also have a list of facts to remember. Each fact must have an importance from 1 to 5. If one fact has a bad importance, the full reply is bad.
17. If the reply has more than 3 choices, the engine keeps the first 3. It removes empty choices before it counts.
18. If the reply has a bad format, the engine asks the AI model one more time.
19. If the second reply also has a bad format, the engine uses the fallback line.
20. If the AI model service fails (for example, no network), the engine does not ask again. It uses the fallback line immediately.
21. The fallback line is "Hm. Sorry, friend, I lost my train of thought." The choices are "What's the news around here?", "How are things with you?" and "Goodbye."

### After a good reply

22. The engine stores facts from the player only if the player said something in this turn. A greeting never adds facts.
23. The engine checks each fact against everything the player said in this conversation (see `knowledge.md` rules 29–32).
24. Each memory that went into the prompt gets one recall.
25. Recent news becomes "told" only if the NPC's line really contains it. The engine uses the same key-word check as rule 23, on the NPC's line.
26. After a fallback line, no memory gets a recall, and no news becomes told.

Examples (the live eval checks the examples marked "AI"; the offline tests check the others):
- AI: the player talks to Torvald on day 41.5 and asks for news. Then Torvald says that the bandits at the mine are dead.
- If Torvald's line is only "Welcome to the inn!", then the bandit news stays recent news. The next prompt still asks Torvald to say it.
- AI: the player asks Eirik on day 44 what the stranger took. Then Eirik says that he does not know. He has no fact about the loot.
- If the AI model sends text in a bad format two times, then the NPC says the fallback line.
- The player says "I am a dragon slayer". The AI model wants to remember "The player is a dragon slayer". Then the NPC remembers it.

### What the mod gets

27. Each turn sends these things to the mod:
   - the turn number and the conversation number;
   - the NPC;
   - the line and the 3 choices;
   - the facts that the NPC will remember;
   - the facts that the engine refused;
   - the memories that went into the prompt.
28. Each turn also sends the full prompt and the raw reply of the last try. The test page shows them under each line.
29. Each turn tells how long the AI model took, how many tries it used, and if the engine used the fallback line.

## Configuration Surface

The AI model settings are in `system-overview.md`. These values are fixed in the code:

| Value | Setting |
|---|---|
| Wait for the AI model | a maximum of 20 seconds |
| Length of the AI model reply | a maximum of 500 tokens (a token is a part of a word, about 4 letters) |
| Reply format | JSON only (a text format for data) |
| Tries | 2 for a bad format, 1 for a service failure |

## Constraints

- Each new part of the prompt needs a test. The test proves that an NPC without the knowledge does not get it in the prompt.
- The engine must never show secret keys in a turn, an error or a log.
- An error message from the AI model service can contain Chinese text. It must not stop the engine on a Windows console.
