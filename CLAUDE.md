# genpc-ai

A game-agnostic engine for generative-AI NPCs. A deterministic knowledge model sits in front of the LLM and decides who knows what: witnesses, gossip that loses detail, decay over in-game time, and knowledge that follows save files. Game mods are thin HTTP clients. The project overview is in `README.md`, and plans are in `.omc/plans/`.

## Specs
All specifications live in `.ai/spec/`. Start with `.ai/spec/README.md` for the overview, reading order and structure. `ARCHITECTURE.md` is the human-facing overview.
- `what/` (behaviour), `glossary.md`, `constraints.md`, `decisions/` and the Summary of every spec PR **must** be written in extremely simple, plain English, following ASD-STE100 where possible. Follow "Writing rules for what/" in `.ai/spec/README.md`, and use the `glossary.md` word for each thing.
- `how/` (code map) uses the same simple sentences but the code's exact names. Follow "Writing rules for how/" in `.ai/spec/README.md`.
- A PR that changes a `what/` rule lists each changed rule (file and number) in plain words in its Summary.
- `main` always describes what the engine does now. New rules reach `main` in the same PR as the code that builds them. `[PLANNED: #N]` on `main` is rare: only for a spec the owner chose to merge ahead of its code. A PR that changes behaviour must update the matching `what/` and `how/` files.

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
- **The owner reviews behaviour, not code.** The owner doesn't read code. Each change to what an NPC, a mod or a player experiences is **one PR in two stages**: first the spec, then the code.
  - Goals and early questions stay on the issue. The spec itself is in the PR, not in an issue comment.
  - **Spec stage.** Branch `spec/<issue>-<slug>`. The first commits change only `.ai/spec/` files: the new rules in `what/` marked `[PLANNED: #N]` (so reviewers can see them), plus glossary words.
    - The Summary is the plain-language spec: what it does, 3–6 concrete examples ("if the player does X, then Y"), what it deliberately won't do, and questions for the owner, each with a recommended answer. No code, no jargon: follow "Writing rules for what/" in `.ai/spec/README.md`. Write "Spec for #N", not "Closes #N", in this stage.
    - The other template sections in this stage: **Testing** = the checks output (no code yet); **Local AI review** = one review against "Writing rules for what/", the existing rules, and `REVIEW.md` §7; **Risk** = "spec stage: no code yet"; **How to revert** = close the PR.
    - Approval is the owner's "OK" comment on the PR. (PRs are opened from the owner's account, so GitHub's Approve button is not available to them.) If the owner answers a question differently, update the rules and the Summary, post the changed rules in a comment, and get the owner's OK again. When the owner says OK, reply on the PR with the commit SHA that the OK covers.
  - **Code stage.** Only after the OK: add the code and the tests to the same PR. The tests check the spec's examples. Remove the `[PLANNED: #N]` marks, update `how/`, and add "Closes #N" to the Summary. Leave the approved plain-language part of the Summary as it is; add code detail under it. Update Testing, Risk and How to revert for the code. In Local AI review, keep the spec-stage review and add the code reviews below it. If the code shows that an approved rule must change, post the change and get the owner's OK on it first.
  - **Merge** only when the owner's OK covers the final rules, the code stage is done, CI is green and the reviews are clean. Never merge the spec stage alone, unless the owner asks for that; then the rules stay `[PLANNED: #N]` on `main` and a later PR builds them.
- Make small PRs to `main` and squash-merge them. Branch names: `spec/`, `feat/`, `fix/`, `docs/`, `chore/`.
- Before opening a PR:
  1. Run the checks.
  2. Run a **local AI review** with `/code-review` on the branch, or a fresh-context subagent review against `REVIEW.md`.
  3. Fix the findings or explain why they don't apply.
  4. Fill in every section of the PR template. CI rejects a PR whose "Local AI review" section is empty.
- **The AI review is the code gate. Risk sets how thorough it is:**
  - **low** (docs, plans): checks plus one review;
  - **medium** (engine or mod code): checks plus one review, with every finding fixed or answered;
  - **high** (`knowledge.py`, prompt building, save/load, `.github/`): add a **second, independent** review that gets only the diff and the approved spec (the `what/` rules at the commit the owner said OK to, plus the plain-language part of the Summary), never the first review's conclusions, plus the live eval if the prompt or knowledge rules changed.
- Once CI is green and the reviews are clean, the PR is ready to merge. A behaviour PR also needs the owner's OK and a finished code stage (see above). Tell the owner in a line or two of plain language what changed for the player or the mod. Never ask them to read a code diff. In a behaviour PR, the owner reads the Summary and may comment on the plain-English rules.

## Non-goals (for now)
Lip sync, speech input, local LLMs, paid Cyberpunk content, and publishing to Nexus without the owner's approval.
