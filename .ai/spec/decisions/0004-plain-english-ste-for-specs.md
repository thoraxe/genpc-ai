# 0004: Behaviour specs use plain English and ASD-STE100

**Status:** accepted
**Date:** 2026-11-10

## Context

The owner and other human reviewers approve behaviour from the specs (see decision 0003). Technical words and long sentences make the specs hard to understand. A reviewer who does not understand a rule cannot approve it correctly.

## Decision

- We use spec-first. Behaviour rules are in `.ai/spec/what/`. The code map is in `.ai/spec/how/`.
- Every `what/` file, the glossary, the constraints, the decisions, and every plain-language spec in an issue use extremely simple, plain English.
- We follow ASD-STE100 (Simplified Technical English) where possible: short sentences, one idea in each sentence, active voice, simple tenses, and one word for one thing.
- `glossary.md` gives the one word for each thing.
- `how/` files are for AI agents. They can use technical language.

The writing rules are in "Writing rules for what/" in `../README.md`.

## Other options

- **Normal technical English in every spec.** We did not choose this. The owner cannot review it easily.
- **Full ASD-STE100 with the official dictionary.** We did not choose this now. The dictionary is not in the repo, and technical names (routes, fields) are necessary. We follow the rules where possible.

## Results

- Easier: a human reviewer can read each rule and check each example.
- Harder: specs are longer, because each sentence has only one idea. Writers must check the glossary.
