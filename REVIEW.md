# Review guide

What a reviewer, human or AI, should look for in this repo, in priority order. When the same comment keeps coming up, add it here, or better, turn it into a test or a lint rule.

## 1. Knowledge leaks (highest)
The product's core promise is that an NPC can't say what it doesn't know.
- `build_system_prompt` and anything it calls may include only the NPC's bio, the setting, and the `MemoryView`s returned by `knowledge.retrieve` for **that** NPC.
- `MemoryView.dropped_facts` and forgotten views must not reach the prompt. Gist views do reach it, but only with their `kept_facts` and a "vaguely remember" note.
- New prompt fields need an offline test proving that an NPC without the knowledge doesn't get it, modelled on `test_prompt_contains_only_that_npcs_knowledge` in `poc/tests/test_dialog.py`.

## 2. Determinism of the knowledge rules
- Nothing in `knowledge.py` may depend on randomness, wall-clock time or the LLM. It depends only on stored state, in-game time and `Rules`.
- Gossip and decay changes need tests that check exact values or thresholds.
- The clock only moves forward. A backwards change is a load, never an advance.

## 3. Save/load correctness
- A snapshot must capture all state that affects what an NPC knows or says: events, memories, turns, the clock and the `mentioned` flags.
- After a load, nothing from the abandoned timeline may survive.

## 4. Trusting LLM output
- Treat model JSON as untrusted. Validate it with pydantic, retry once, then use the fallback line.
- A `remember` fact is stored only if it is grounded in what the player said.
- News is marked as told only when the NPC's line actually contains it.

## 5. Secrets and the outside world
- No key values in code, logs, test fixtures, PR text or error messages. `.env` stays ignored.
- Provider errors must not surface raw credentials. Chinese error text from z.ai must not crash Windows consoles (cp1252).

## 6. API compatibility with game mods
- The `/api/*` request and response shapes are a contract with the mods. Adding a field is fine, but renaming or removing one needs a note in the PR and a matching mod change.

## 7. Spec PRs
A spec PR changes only `.ai/spec/`. Check:
- The Summary and the new rules follow "Writing rules for what/" in `.ai/spec/README.md`, and use the glossary words.
- Each rule is testable, has a real-value example where it has a number, and is marked `[PLANNED: #N]`.
- The Summary has 3–6 examples, what it will not do, and questions with recommended answers.
- New rules do not contradict or renumber existing rules, and do not clash with other open spec PRs.
- Nothing in the spec would put another NPC's knowledge, world state, lost facts or faded facts into a prompt (§1).

## Not worth flagging
- Styling of the test UI in `poc/ui/`. It's deliberately bare.
- Long lines in strings or comments (ruff's formatter owns the layout).
