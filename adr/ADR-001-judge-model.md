# ADR-001 — Judge model selection and locking

Status: accepted · 2026-06-06

## Context

LLM-as-judge scores agent behavior where deterministic checks cannot (faithfulness,
helpfulness, "did it actually answer the contract"). The judge is itself an LLM, so two
risks appear: judge drift (same output scored differently across runs/model versions) and
judge bias (favoring verbose or fluent answers).

## Decision

1. **Pin the judge model explicitly** (default `gpt-4o-mini`, `temperature=0`). The model id
   is a config value, recorded in every report. Comparing two runs is only valid when the
   judge model matches.
2. **Version-lock the judge prompt** (`JUDGE_PROMPT_VERSION` in `core/judge.py`). Editing the
   prompt requires bumping the version and re-validating against the human-labeled meta-set.
3. **Judge returns score AND confidence.** Low-confidence judgments do not pass on their own;
   they fall through to a fail so a human reviews them. Conservative by default.
4. **Deterministic checks gate first.** The judge never overrides a failed tool-call or
   schema check. Judge only decides the soft dimensions.

## Consequences

- Reports across judge-prompt versions are not directly comparable — by design.
- A small human-labeled meta-set (`datasets/_meta/`) is the calibration anchor; planned.
