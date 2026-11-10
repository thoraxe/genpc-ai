# 0003: The owner approves behaviour, an AI review checks the code

**Status:** accepted
**Date:** 2026-11-10

## Context

The owner decides what the product does, but does not read code. A code review by the owner is thus not useful.

## Decision

- Before a change to what an NPC, a mod or a player sees, write a plain-language spec in an issue comment.
- The spec tells what the change does, gives 3 to 6 examples, and tells what it will not do.
- Wait for the owner's OK. The tests check the examples.
- An AI review checks the code before each PR. High-risk changes get a second, independent AI review.
- When the PR is ready, tell the owner in one or two plain sentences what changed for the player or the mod.

## Other options

- **The owner reads each PR.** We did not choose this. The owner does not read code.
- **No review.** We did not choose this. Knowledge leaks are the main risk, and a review finds them.

## Results

- Easier: the owner controls behaviour without reading code.
- Harder: each behaviour change waits for the owner's OK before the work starts.
