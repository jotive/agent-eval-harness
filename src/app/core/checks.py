from __future__ import annotations

import json

from jsonschema import Draft7Validator

from app.schemas import AgentTrace, CheckResult, Expect, ToolCallExpect


def _tool_matches(expected: ToolCallExpect, trace: AgentTrace) -> tuple[bool, str]:
    candidates = [tc for tc in trace.tool_calls if tc.name == expected.name]
    if not candidates:
        called = [tc.name for tc in trace.tool_calls] or ["<none>"]
        return False, f"tool '{expected.name}' not called. called: {called}"

    if expected.args_subset is None:
        return True, f"tool '{expected.name}' called"

    for call in candidates:
        if all(call.args.get(k) == v for k, v in expected.args_subset.items()):
            return True, f"tool '{expected.name}' called with expected args"

    return False, f"tool '{expected.name}' called but args_subset {expected.args_subset} not matched"


def run_checks(expect: Expect, trace: AgentTrace) -> list[CheckResult]:
    results: list[CheckResult] = []

    for tool in expect.tools:
        passed, detail = _tool_matches(tool, trace)
        results.append(CheckResult(name=f"tool:{tool.name}", passed=passed, detail=detail))

    for needle in expect.contains:
        passed = needle.lower() in trace.output.lower()
        results.append(
            CheckResult(name=f"contains:{needle}", passed=passed, detail="" if passed else "substring missing")
        )

    for needle in expect.not_contains:
        passed = needle.lower() not in trace.output.lower()
        results.append(
            CheckResult(name=f"not_contains:{needle}", passed=passed, detail="" if passed else "forbidden substring present")
        )

    if expect.output_schema is not None:
        results.append(_check_schema(expect.output_schema, trace))

    if expect.max_cost_usd is not None:
        passed = trace.cost_usd <= expect.max_cost_usd
        results.append(
            CheckResult(
                name="budget:cost",
                passed=passed,
                detail=f"{trace.cost_usd:.4f} <= {expect.max_cost_usd}" if passed else f"over budget: {trace.cost_usd:.4f} > {expect.max_cost_usd}",
            )
        )

    if expect.max_latency_ms is not None:
        passed = trace.latency_ms <= expect.max_latency_ms
        results.append(
            CheckResult(name="budget:latency", passed=passed, detail=f"{trace.latency_ms}ms vs {expect.max_latency_ms}ms")
        )

    if expect.max_steps is not None:
        passed = trace.steps <= expect.max_steps
        results.append(
            CheckResult(name="budget:steps", passed=passed, detail=f"{trace.steps} steps vs max {expect.max_steps}")
        )

    return results


def _check_schema(schema: dict, trace: AgentTrace) -> CheckResult:
    try:
        payload = json.loads(trace.output)
    except json.JSONDecodeError as exc:
        return CheckResult(name="output_schema", passed=False, detail=f"output not valid JSON: {exc}")

    errors = sorted(Draft7Validator(schema).iter_errors(payload), key=lambda e: e.path)
    if errors:
        first = errors[0]
        return CheckResult(name="output_schema", passed=False, detail=f"schema violation: {first.message}")

    return CheckResult(name="output_schema", passed=True)
