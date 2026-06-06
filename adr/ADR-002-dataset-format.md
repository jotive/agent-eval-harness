# ADR-002 — Dataset format and versioning

Status: accepted · 2026-06-06

## Context

Eval examples must be diffable, reviewable in PRs, and express a *behavior contract* rather
than a brittle expected-output string. Agent outputs are non-deterministic; asserting exact
text produces flaky evals that teams learn to ignore.

## Decision

- Datasets are **YAML files under `datasets/`**, versioned with the code.
- Each case has an `id` (stable, unique — enforced at load), an `input`, and an `expect`
  block. `expect` mixes:
  - **deterministic** assertions: `tools` (tool called with optional args subset),
    `contains` / `not_contains`, `output_schema` (JSON Schema), and budgets
    (`max_cost_usd`, `max_latency_ms`, `max_steps`).
  - **judged** assertion: `judge` — a natural-language behavior contract scored by the LLM judge.
- A case may use either or both. Deterministic checks gate before the judge runs.
- Case `id`s are stable across edits so regression detection can match case-to-case between a
  baseline report and a new run.

## Consequences

- Adding a capability = add a case, review the contract in PR.
- Renaming a case `id` breaks its regression history — treated like deleting + adding.
