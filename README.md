# agent-eval-harness

Evaluation harness for LLM agents. Golden datasets + LLM-as-judge scoring + deterministic checks. Run an agent against the harness and get pass/fail per example with structured failure diagnostics, a cost/latency breakdown, and CI-grade regression detection against a baseline.

---

## The problem

Agents fail silently. They produce output that looks right and is wrong. Without eval, the only feedback loop is the user, which is expensive feedback. This harness makes the silent failures loud and reproducible, and turns "did this change break the agent" into a CI exit code.

## What it does

- **Eval at the behavior level, not the output-text level.** A case asserts a *behavior contract* (called the right tool, stayed grounded, did not leak PII, returned valid JSON, stayed under budget), not a brittle expected string.
- **Hybrid scoring.** Deterministic checks (tool called with X args, `contains`/`not_contains`, JSON Schema, cost/latency/step budgets) run first and gate. The LLM judge scores the soft dimensions (faithful, helpful, on-task) only after.
- **LLM-as-judge with confidence gating.** Judge model is pinned, judge prompt is version-locked (`JUDGE_PROMPT_VERSION`), and low-confidence judgments fall through to a fail so a human reviews them. Conservative by default. See `adr/ADR-001-judge-model.md`.
- **Golden datasets as code.** Examples live in versioned YAML under `datasets/`, diffable and reviewable in PRs. See `adr/ADR-002-dataset-format.md`.
- **Regression detection.** Compare a run against a baseline report. Any case that passed before and fails now, or a pass-rate drop beyond threshold, is a regression and the CLI exits non-zero. Wire it into CI.

## Install

```bash
pip install -e ".[dev]"
```

## Run

```bash
# Eval the built-in demo agent against the example dataset
eval run --dataset datasets/example.yaml

# Eval your own agent (a "module:factory" returning an async callable)
eval run --dataset datasets/example.yaml --agent mypkg.agent:make_agent --out report.json

# Gate against a baseline (non-zero exit on regression)
eval run --dataset datasets/example.yaml --baseline baselines/main.json --max-drop 0.0
```

Your agent is any `module:factory` where the factory returns an async callable `(EvalCase) -> AgentTrace`. The trace reports the output, tool calls, step count, cost, and latency. See `src/app/core/agent.py` for the `DemoAgent` reference implementation and the `AgentUnderTest` protocol.

The judge needs `OPENAI_API_KEY`. Cases with only deterministic checks run without any API key.

## Stack

Python 3.12 · Pydantic v2 · OpenAI SDK · jsonschema · typer + rich CLI · pytest · GitHub Actions for CI. The unit tests are deterministic and make no API calls.

## Roadmap

| Milestone | Status |
|---|---|
| Repo scaffold | ✅ |
| ADR-001 — judge model selection + locking | ✅ |
| ADR-002 — dataset format + versioning | ✅ |
| Runner CLI: `eval run --dataset X --agent Y` | ✅ |
| Built-in checks: tool call assertions, output schema, budgets | ✅ |
| LLM-as-judge with confidence threshold | ✅ |
| CI integration with regression detection | ✅ |
| Human-labeled meta-set for judge calibration | ⬜ |
| Langfuse / OTEL trace export | ⬜ |

## Author

[Jotive](https://github.com/jotive) · [dev.jotive.com.co](https://dev.jotive.com.co)
