# 0005: Each spec is a PR

**Status:** accepted
**Date:** 2026-11-10

## Context

Decision 0003 put each plain-language spec in an issue comment. Then decision 0004 made the `what/` files the home of all behaviour rules. Thus we wrote each rule two times: once in the issue comment, and once in the `what/` file. The two copies can be different. Also, answers and changes in an issue thread are hard to follow.

## Decision

- Goals and early questions stay on the issue.
- Each spec is a PR. The PR adds the new rules to the `what/` files, marked `[PLANNED: #N]`.
- The PR description is the plain-language spec: what it does, 3 to 6 examples, what it will not do, and questions for the owner.
- The owner approves the PR, or writes "OK". Then we merge it. We never merge a spec PR without the owner's OK.
- The code PR comes after it. It changes the rules to `[DONE: #N]`.

This replaces the "issue comment" step of decision 0003. The rest of 0003 stays.

## Other options

- **Keep specs in issue comments.** We did not choose this. We must copy each rule into the `what/` files, and the copy can be wrong.
- **Put the spec and the code in one PR.** We did not choose this. The owner must approve the behaviour before the code work starts.

## Results

- Easier: the owner approves the exact rules that go into the project. The owner can comment on one rule. Two specs that change the same rule show a conflict.
- Harder: each feature has two PRs, a spec PR and a code PR.
