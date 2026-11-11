# Decisions

Each file records one important decision: what we chose, why, and what we did not choose.

## Format

- File name: `NNNN-short-slug.md`, for example `0005-file-ipc-fallback.md`. Numbers go up by one. Do not use a number again.
- Write the decision in the same plain English as `what/` files (see "Writing rules for what/" in `../README.md`). The owner must understand it.
- Sections:
  - **Status:** proposed, accepted, or replaced by `NNNN`.
  - **Date:** the day of the decision (YYYY-MM-DD).
  - **Context:** the problem. What made us choose?
  - **Decision:** what we chose.
  - **Other options:** what we did not choose, and why.
  - **Results:** what is now easier, and what is now harder.
- Do not change an accepted decision. If we change our mind, write a new decision and mark the old one "replaced by `NNNN`".

## List

| Number | Decision |
|---|---|
| [0001](0001-fixed-knowledge-rules-before-the-ai-model.md) | Fixed rules decide what an NPC knows. The AI model only writes the words. |
| [0002](0002-mods-are-small-http-clients.md) | Game mods are small programs that talk to the engine over HTTP. |
| [0003](0003-owner-reviews-behaviour-ai-reviews-code.md) | The owner approves plain-language specs. An AI review checks the code. |
| [0004](0004-plain-english-ste-for-specs.md) | Behaviour specs use plain English and ASD-STE100. |
| [0005](0005-specs-are-prs.md) | Each spec is a PR that changes the `what/` files. The owner approves the PR. |
| [0006](0006-spec-and-code-in-one-pr.md) | The spec and its code are one PR. They go into `main` together. |
| [0007](0007-mods-in-this-repo.md) | Mods live in this repo, each in its own folder with its own specs. |
