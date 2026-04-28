# agent-eval-harness

> Status: **planned** — repo scaffold. Code lands as the design solidifies.

Evaluation harness for LLM agents. Dataset of golden examples + LLM-as-judge scoring + deterministic checks. Run an agent against the harness and get pass/fail per example with structured failure diagnostics.

---

## What this will demonstrate

- **Eval discipline applied to agentic systems** — beyond unit tests. Pass/fail at the *behavior* level, not the *output text* level.
- **LLM-as-judge with calibration** — judge prompt is itself version-controlled and tested against a meta-set of human-labeled cases. Prevents judge drift.
- **Golden datasets as code** — examples live in versioned `datasets/` with input + expected behavior contract, not just expected output.
- **Hybrid scoring** — deterministic checks (tool was called with X args) + LLM judgment (response was helpful, faithful, on-task). Both reported.
- **Regression alerts** — eval results land in CI; pipeline fails on regression > threshold.

## Tentative stack

Python 3.12 · pytest + custom runners · OpenAI / Anthropic SDK · Pydantic v2 · CLI for local + GitHub Actions for CI · Optional Langfuse export

## Roadmap

| Milestone | Status |
|---|---|
| Repo scaffold | ✅ |
| ADR-001 — judge model selection + locking | ⬜ |
| ADR-002 — dataset format + versioning | ⬜ |
| Runner CLI: `eval run --dataset X --agent Y` | ⬜ |
| Built-in checks: tool call assertions, output schema, faithfulness | ⬜ |
| LLM-as-judge with confidence threshold | ⬜ |
| CI integration with regression detection | ⬜ |

## Why eval matters in production

Agents fail silently. They produce output that looks right and is wrong. Without eval, the only feedback loop is the user — which is expensive feedback. This harness makes the silent failures loud and reproducible.

## Author

[Jotive](https://github.com/jotive) · [dev.jotive.com.co](https://dev.jotive.com.co)
