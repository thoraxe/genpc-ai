# 0005: Each spec is a PR

**Status:** accepted
**Date:** 2026-11-10

## Context

Decision 0003 put each plain-language spec in an issue comment. Then decision 0004 put all behaviour rules in the `what/` files. Thus we wrote each rule two times: once in the issue comment, and once in the `what/` file. The two copies can be different. Also, answers and changes in an issue are hard to follow.

## Decision

- Goals and early questions stay on the issue.
- Each spec is a PR. The PR adds the new rules to the `what/` files, marked `[PLANNED: #N]`.
- The spec PR changes only `.ai/spec/` files. It does not close the issue.
- The PR Summary is the plain-language spec. It gives what the change does, 3 to 6 examples, and what it will not do.
- The Summary also gives questions for the owner. Each question has a recommended answer.
- The owner writes "OK" on the PR. Then we merge it. We never merge a spec PR without the owner's OK.
- If the rules change after the OK, we show the owner the changed rules. Then we wait for a new OK.
- The code PR comes after it. It changes the rules to `[DONE: #N]`.
- If the code PR must change an approved rule, the owner must approve that change first.

This replaces the "issue comment" step of decision 0003. The rest of 0003 stays.

The specs for #7 to #11 are now issue comments. They move into spec PRs. After that, the comments are only history.

## Other options

- **Keep specs in issue comments.** We did not choose this. We must copy each rule into the `what/` files. The copy can be wrong.
- **Put the spec and the code in one PR.** We did not choose this. The owner must approve the behaviour before the code work starts.
- **Use the GitHub "Approve" button.** We did not choose this. The PRs come from the owner's own account, and GitHub does not let a person approve their own PR.

## Results

- Easier: the owner approves the exact rules that go into the project. The owner can comment on one rule. If two spec PRs change the same rule, GitHub shows the problem.
- Harder: each change in behaviour has two PRs, a spec PR and a code PR.
