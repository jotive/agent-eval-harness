from app.core.checks import run_checks
from app.schemas import AgentTrace, Expect, ToolCallExpect, ToolCallRecord


def _trace(**kw):
    base = dict(output="", tool_calls=[], steps=1, cost_usd=0.0, latency_ms=0)
    base.update(kw)
    return AgentTrace(**base)


def test_tool_called_with_args_subset_passes():
    trace = _trace(tool_calls=[ToolCallRecord(name="search_docs", args={"query": "refund", "k": 5})])
    expect = Expect(tools=[ToolCallExpect(name="search_docs", args_subset={"query": "refund"})])
    [check] = run_checks(expect, trace)
    assert check.passed


def test_tool_not_called_fails():
    trace = _trace(tool_calls=[])
    expect = Expect(tools=[ToolCallExpect(name="search_docs")])
    [check] = run_checks(expect, trace)
    assert not check.passed


def test_not_contains_catches_leak():
    trace = _trace(output="here is alice@gmail.com")
    expect = Expect(not_contains=["@gmail.com"])
    [check] = run_checks(expect, trace)
    assert not check.passed


def test_output_schema_rejects_bad_json():
    trace = _trace(output='{"order_id": "A-1"}')  # missing 'total'
    expect = Expect(output_schema={"type": "object", "required": ["order_id", "total"]})
    [check] = run_checks(expect, trace)
    assert not check.passed


def test_output_schema_accepts_valid():
    trace = _trace(output='{"order_id": "A-1", "total": 42.5}')
    expect = Expect(output_schema={"type": "object", "required": ["order_id", "total"]})
    [check] = run_checks(expect, trace)
    assert check.passed


def test_step_budget_fails_when_over():
    trace = _trace(steps=5)
    expect = Expect(max_steps=3)
    [check] = run_checks(expect, trace)
    assert not check.passed
