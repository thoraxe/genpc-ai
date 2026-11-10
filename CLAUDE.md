# genpc-ai

A game-agnostic engine for generative-AI NPCs. A deterministic knowledge model sits in front of the LLM and decides who knows what: witnesses, gossip that loses detail, decay over in-game time, and knowledge that follows save files. Game mods are thin HTTP clients. The project overview is in `README.md`, and plans are in `.omc/plans/`.

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
- Make small PRs to `main` and squash-merge them. Branch names: `feat/`, `fix/`, `docs/`, `chore/`.
- Before opening a PR:
  1. Run the checks.
  2. Run a **local AI review** with `/code-review` on the branch, or a fresh-context subagent review against `REVIEW.md`.
  3. Fix the findings or explain why they don't apply.
  4. Fill in every section of the PR template. CI rejects a PR whose "Local AI review" section is empty.
- **Risk sets the review:**
  - **low** (docs, plans): may merge once CI is green;
  - **medium** (engine or mod code): the owner approves;
  - **high** (`knowledge.py`, prompt building, save/load, `.github/`): the owner reads the diff.

## Non-goals (for now)
Lip sync, speech input, local LLMs, paid Cyberpunk content, and publishing to Nexus without the owner's approval.
