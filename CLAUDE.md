# genpc-ai

A game-agnostic engine for generative-AI NPCs. A deterministic knowledge model sits in front of the LLM and decides who knows what: witnesses, gossip that loses detail, decay over in-game time, and knowledge that follows save files. Game mods are thin HTTP clients. The project overview is in `README.md`, and plans are in `.omc/plans/`.

## Specs
All specifications live in `.ai/spec/`. Start with `.ai/spec/README.md` for the overview, reading order and structure. `ARCHITECTURE.md` is the human-facing overview.
- `what/` (behaviour), `glossary.md`, `constraints.md`, `decisions/` and the description of every spec PR **must** be written in extremely simple, plain English, following ASD-STE100 where possible. Follow "Writing rules for what/" in `.ai/spec/README.md`, and use the `glossary.md` word for each thing.
- `how/` (code map) uses the same simple sentences but the code's exact names. Follow "Writing rules for how/" in `.ai/spec/README.md`.
- A PR that changes a `what/` rule lists each changed rule (file and number) in plain words in its Summary.
- A spec PR adds the new rules to the right `what/` files, marked `[PLANNED: #N]`. The code PR that builds it updates the rules and marks them `[DONE: #N]`. A PR that changes behaviour must update the matching `what/` and `how/` files.

## Stack
- Python 3.12+ managed with **uv** (never pip or venv).
- FastAPI, SQLite, pydantic v2, the openai SDK (any OpenAI-compatible LLM), and httpx (ElevenLabs).
- The code is in `poc/engine/`, with tests in `poc/tests/`.

## Checks: run them, and paste the output into the PR
```
uv run ruff check poc
uv run ruff format --check poc
uv run pytest -q
```
If you changed `knowledge.py` or the prompt, retrieval or validation in `dialog.py`, also run the live eval and paste its summary. It needs `.env`.
```
uv run python poc/scripts/eval.py 10
```

## Conventions
- **The engine core has no game-specific logic.** Settings, places and casts live in `poc/data/*.json`, and game behaviour lives in the mods.
- **The prompt contains only facts retrieved for that NPC.** Never put world state or other NPCs' memories in it.
- **The knowledge rules are deterministic and tunable through `Rules`.** No LLM calls inside `knowledge.py`.
- **Secrets live only in `.env`.** Never print, log or commit key values.
- **Every bug fix adds a regression test.**

## Workflow
- **The owner reviews behaviour, not code.** The owner doesn't read code. Before coding anything that changes what an NPC, a mod or a player experiences, open a **spec PR** and wait for the owner to approve it.
  - Goals and early questions stay on the issue. The spec itself is a PR, not an issue comment.
  - Branch `spec/<issue>-<slug>`. The PR changes only `.ai/spec/` files: the new rules in `what/` marked `[PLANNED: #N]`, plus glossary words. Write "Spec for #N", not "Closes #N": the issue stays open until the code is done.
  - The PR description (Summary section) is the plain-language spec: what it does, 3–6 concrete examples ("if the player does X, then Y"), what it deliberately won't do, and questions for the owner, each with a recommended answer. No code, no jargon: follow "Writing rules for what/" in `.ai/spec/README.md`.
  - Approval is the owner's GitHub approval or an "OK" comment. Then merge the spec PR. Never merge a spec PR without the owner's OK. If the owner answers a question differently, update the rules before merging.
  - The code PR follows, links the issue ("Closes #N"), and changes the rules to `[DONE: #N]`. The tests check the spec's examples.
- Make small PRs to `main` and squash-merge them. Branch names: `spec/`, `feat/`, `fix/`, `docs/`, `chore/`.
- Before opening a PR:
  1. Run the checks.
  2. Run a **local AI review** with `/code-review` on the branch, or a fresh-context subagent review against `REVIEW.md`.
  3. Fix the findings or explain why they don't apply.
  4. Fill in every section of the PR template. CI rejects a PR whose "Local AI review" section is empty.
- **The AI review is the code gate. Risk sets how thorough it is:**
  - **low** (docs, plans): checks plus one review;
  - **medium** (engine or mod code): checks plus one review, with every finding fixed or answered;
  - **high** (`knowledge.py`, prompt building, save/load, `.github/`): add a **second, independent** review that gets only the diff and the approved spec, never the first review's conclusions, plus the live eval if the prompt or knowledge rules changed.
- Once CI is green and the reviews are clean, the PR is ready to merge. Tell the owner in a line or two of plain language what changed for the player or the mod. Never ask them to read a diff.

## Non-goals (for now)
Lip sync, speech input, local LLMs, paid Cyberpunk content, and publishing to Nexus without the owner's approval.
