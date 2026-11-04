# ADR-003 — Judge reliability: strict parsing and fail-closed scoring

Status: accepted · 2026-11-04

## Context

ADR-001 pins the judge model and prompt and gates on confidence. It does not cover the
judge failing at runtime: API errors, empty or non-JSON replies, JSON of the wrong shape,
or scores outside 0..1. Previously a malformed reply raised inside the run, aborting every
other case, and out-of-range values such as `score: 1.5` were accepted and passed.

## Decision

1. **Strict verdict parsing.** `parse_verdict` in `core/judge.py` accepts only a JSON object
   whose `score` and `confidence` are numeric and within 0..1. Anything else raises
   `JudgeError`. A missing field counts as `0.0`, which fails the gate.
2. **Fail closed per case.** `run_dataset` catches judge errors, logs `judge_error`, and
   records the case as failed with `error="judge failed: ..."`. Deterministic check results
   are kept. Other cases keep running.
3. **No silent retries or fallbacks.** The judge is not retried and no default score is
   substituted, so results stay comparable and a judge outage shows as failures.
4. **Judge stubbed in tests.** Tests replace the client with a deterministic stub. Scoring
   must produce identical reports across repeated runs and concurrency levels.

## Consequences

- A judge outage fails judged cases instead of crashing the run; the regression gate flags them.
- Cases without a `judge` contract are unaffected.
- Public signatures are unchanged. `Judge.score` now raises `JudgeError` (a `ValueError`)
  on malformed output where it previously raised `json.JSONDecodeError`/`AttributeError` or
  accepted out-of-range values.
- Retry with backoff for transient API errors and judge-agreement sampling remain future work.
