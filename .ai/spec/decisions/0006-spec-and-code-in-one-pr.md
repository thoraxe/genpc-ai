# 0006: The spec and its code are one PR

**Status:** accepted
**Date:** 2026-11-10

## Context

Decision 0005 merged each spec PR before its code. The new rules then were on `main`, but the engine did not do them yet. Only the `[PLANNED: #N]` mark told the reader. A reader can miss the mark. Then the reader thinks that the engine does something that it does not do.

## Decision

- A change in behaviour is one PR in two stages.
- **Spec stage:** the PR has only the new rules and the plain-language Summary. The owner writes "OK".
- **Code stage:** after the OK, we add the code and the tests to the same PR. We remove the `[PLANNED: #N]` marks.
- We merge the PR only when the code stage is done. Thus the rules and the code go into `main` together.
- If a rule changes after the OK, the owner must give a new OK.
- The owner can ask to merge a spec before its code. Then its rules stay `[PLANNED: #N]` on `main`.

This replaces the "merge the spec first" part of decision 0005. The rest of 0005 stays.

The spec for #8 is already on `main` with `[PLANNED: #8]` marks. Its code PR removes the marks.

## Other options

- **Merge the spec first, with `[PLANNED: #N]` marks (decision 0005).** We did not keep this. The rules on `main` did not always tell what the engine does.
- **A spec PR and a separate code PR that waits for it.** We did not choose this. It gives two PRs for one change, and the spec still waits on a branch.

## Results

- Easier: the rules on `main` always tell what the engine does now.
- Easier: one PR for each change in behaviour.
- Harder: a spec PR stays open longer. When `main` changes, we must update the open spec PRs.
- Harder: a spec cannot refer to a rule in an open PR. Build the earlier change first.
