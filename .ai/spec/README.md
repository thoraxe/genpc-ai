# genpc-ai — Specifications

genpc-ai is an engine for AI characters (NPCs) in games. The engine decides what each NPC knows. An AI model only writes the words that the NPC says. These specs tell what the engine must do (`what/`) and where the code for each part is (`how/`).

## Structure

| Layer | Path | Purpose | Written for |
|---|---|---|---|
| **what/** | `.ai/spec/what/` | What the system must do: rules, the HTTP API, data files, settings. | The owner **and** AI agents. Plain English (see "Writing rules for what/"). |
| **how/** | `.ai/spec/how/` | Where the code is: files, call paths, patterns, pitfalls. | AI agents and code reviewers. Simple sentences with the code's own names (see "Writing rules for how/"). |
| **decisions/** | `.ai/spec/decisions/` | Why we made important choices. | Both. |

Also read `glossary.md` (the words we use, each with one meaning) and `constraints.md` (rules for the full project).

## Scope

In scope: the Python engine in `poc/` (knowledge rules, conversations, saves, HTTP API, voice) and its data files.

Out of scope:
- The game mods. The Cyberpunk 2077 mod does not exist yet (see `.omc/plans/cyberpunk-mod-plan.md`). When it exists, it gets its own `what/` file.
- The test web page in `poc/ui/`. It is only a client of the HTTP API.
- The external AI model and the voice service (ElevenLabs). The specs tell only how the engine uses them.

## Audience

- `what/` files: the owner reviews them. The owner does not read code. Every rule must be clear to a person who does not know Python, JSON or HTTP.
- `how/` files: AI agents and human code reviewers. Content is precise and uses the code's names, in simple sentences.

## Quick Start

| Task | Start here |
|---|---|
| Understand the system | `what/system-overview.md`, then `../../ARCHITECTURE.md` |
| Change who knows what (witnesses, gossip, fading) | `what/knowledge.md`, `how/knowledge-engine.md` |
| Change what an NPC says, or the prompt | `what/conversation.md`, `how/dialog-pipeline.md` |
| Change saves, loads or the game clock | `what/saves-and-clock.md`, `how/knowledge-engine.md` |
| Add or change an HTTP route for a mod | `what/http-api.md`, `how/project-structure.md` |
| Add a game world, town or NPC | `what/world-file.md` |
| Run or write tests and the live eval | `how/testing-and-eval.md` |
| Write a spec for the owner | "Writing rules for what/" below |

## Cross-Reference

| what/ | how/ |
|---|---|
| `what/system-overview.md` | `how/project-structure.md` |
| `what/knowledge.md` | `how/knowledge-engine.md` |
| `what/saves-and-clock.md` | `how/knowledge-engine.md` |
| `what/conversation.md` | `how/dialog-pipeline.md` |
| `what/http-api.md` | `how/project-structure.md`, `how/dialog-pipeline.md` (voice) |
| `what/world-file.md` | `how/knowledge-engine.md` |
| (all) | `how/testing-and-eval.md` |

## Writing rules for what/

The owner reviews behaviour, not code. Thus every `what/` file uses **extremely simple, plain English**. We follow **ASD-STE100 (Simplified Technical English)** where possible. These rules apply to every `what/` file, to `glossary.md`, to `constraints.md`, and to the Summary of every spec PR.

**Sentences**
1. Write a maximum of 20 words in a rule or an instruction. Write a maximum of 25 words in a description.
2. Write only one idea in each sentence.
3. Use the active voice. Write "The engine keeps the fact", not "The fact is kept".
4. Use only the simple present, the simple past and the simple future ("keeps", "kept", "will keep").
5. Write instructions as commands: "Send the event", not "The mod should send the event".
6. Use "a", "an" and "the" before nouns. Do not drop them to save words.
7. Write a maximum of 6 sentences in a paragraph. Use a list when you have 3 or more items.

**Words**
8. Use one word for one thing. Use the word that `glossary.md` gives. For example, always write "gossip". Do not write "rumor", "hearsay" or "hop".
9. Use one meaning for one word. For example, "day" always means a day in the game, never a real day.
10. Use simple, common words. Write "use", not "utilize". Write "start", not "initiate". Write "about", not "approximately". Write "if", not "in the event that".
11. Do not use phrasal verbs when a simple verb exists. Write "say", not "bring up". Write "find", not "figure out".
12. Do not use "-ing" words as verbs or adjectives. Write "when the player talks", not "while talking".
13. Do not use idioms, jokes or slang.

**Technical names**
14. You can use technical names: HTTP routes, field names, file names, settings and numbers. Put them in `code` style.
15. Explain each technical name in plain words the first time a file uses it, or link to `glossary.md`.
16. If a rule has a number, give an example with real values. For example: "Gossip goes to the same town after half a day (day 41 → day 41.5)."

**Structure**
17. Put the plain rule first. Put technical detail (exact fields, exact limits) after it, or in a table.
18. Every rule must be testable. A reader must know how to see if the engine obeys it.
19. Give 3 to 6 examples in the form "If the player does X, then Y" for each new behaviour.
20. Write what the change will **not** do.

We do not have the official ASD-STE100 dictionary in the repo. Use the rules above, and choose the simplest common word when you are not sure.

## Writing rules for how/

`how/` files are for AI agents and for human reviewers of code changes. They use the same sentences, but the words of the code.

1. Obey the `what/` rules 1–7 (sentences), 13 (no idioms), 17 (plain point first) and 18 (testable).
2. Do not obey the `what/` rules 8–12 (words). Use the exact names from the code in `code` style, for example `settlement`, `gist`, `hop1`. `glossary.md` gives the plain word for each code name.
3. Tables of files and symbols do not have to obey the sentence rules. Keep each table cell short.
4. Tell the reader which `what/` rules a section implements, for example "(`what/knowledge.md` rules 6–16)".

## Reviewing spec changes

- The owner approves changes to `what/` files. The owner does not need to review `how/` files. The AI review checks them.
- In the PR summary, list each changed `what/` rule by file and number, in plain words. For example: "knowledge.md rule 6: same-town gossip now arrives after 1 day, not half a day."

## Conventions

- **Rule numbering:** rules have numbers in each `what/` file. The numbers do not change. If you remove a rule, leave a gap. If you add a rule between two rules, use a sub-number (16a, 16b). Issues and PRs can then refer to "knowledge.md rule 7".
- **Planned changes:** mark a rule that is not built yet with `[PLANNED: #N]`, where N is the GitHub issue. When the code is done, change the rule text to tell what the code does, and change the mark to `[DONE: #N]`. Later, remove `[DONE]` marks. In a Planned Changes table, strike through a done row (`~~#N~~`). Do not delete it.
- **Specs and the owner's OK:** a spec is a PR (see `CLAUDE.md`). It adds the new rules to the correct `what/` files with `[PLANNED: #N]` marks. Its Summary gives the plain spec, examples, what it will not do, and questions. It does not close the issue. When the owner writes "OK", merge it. The code PR then makes the rules `[DONE: #N]`.
- **Constraints:** a rule for one part goes in the Constraints section of that part's `what/` file. A rule for the full project goes in `constraints.md`. Build, test and code-style rules go in `CLAUDE.md`.
- **Authority:** `what/` is authoritative for behaviour. `how/` is authoritative for code layout. If they do not agree, `what/` is correct and the code is wrong (or the spec needs an approved change).
- **New file or old file:** if a new part has its own settings and you can understand it alone, give it a new file. If it adds a capability to a part, put it in that part's file.
