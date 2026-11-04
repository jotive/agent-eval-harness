from app.core.checks import run_checks
from app.schemas import AgentTrace, Expect, ToolCallExpect, ToolCallRecord


def _trace(**kw):
    base = {"output": "", "tool_calls": [], "steps": 1, "cost_usd": 0.0, "latency_ms": 0}
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


def test_contains_is_case_insensitive():
    [check] = run_checks(Expect(contains=["Refund"]), _trace(output="REFUND window"))
    assert check.passed


def test_contains_missing_fails():
    [check] = run_checks(Expect(contains=["refund"]), _trace(output="nothing"))
    assert not check.passed


def test_not_contains_is_case_insensitive():
    [check] = run_checks(Expect(not_contains=["secret"]), _trace(output="A SECRET"))
    assert not check.passed


def test_empty_expect_yields_no_checks():
    assert run_checks(Expect(), _trace(output="anything")) == []


def test_empty_output_fails_contains():
    [check] = run_checks(Expect(contains=["x"]), _trace(output=""))
    assert not check.passed


def test_tool_wrong_args_fails():
    trace = _trace(tool_calls=[ToolCallRecord(name="t", args={"q": "a"})])
    [check] = run_checks(Expect(tools=[ToolCallExpect(name="t", args_subset={"q": "b"})]), trace)
    assert not check.passed


def test_tool_matches_any_of_several_calls():
    trace = _trace(
        tool_calls=[ToolCallRecord(name="t", args={"q": "a"}), ToolCallRecord(name="t", args={"q": "b"})]
    )
    [check] = run_checks(Expect(tools=[ToolCallExpect(name="t", args_subset={"q": "b"})]), trace)
    assert check.passed


def test_tool_empty_args_subset_matches_any_call():
    trace = _trace(tool_calls=[ToolCallRecord(name="t")])
    [check] = run_checks(Expect(tools=[ToolCallExpect(name="t", args_subset={})]), trace)
    assert check.passed


def test_tool_none_expected_matches_absent_arg():
    trace = _trace(tool_calls=[ToolCallRecord(name="t", args={})])
    [check] = run_checks(Expect(tools=[ToolCallExpect(name="t", args_subset={"q": None})]), trace)
    assert check.passed


def test_budgets_pass_at_exact_limit():
    trace = _trace(steps=3, cost_usd=0.5, latency_ms=100)
    results = run_checks(Expect(max_steps=3, max_cost_usd=0.5, max_latency_ms=100), trace)
    assert len(results) == 3
    assert all(r.passed for r in results)


def test_budgets_fail_when_exceeded():
    trace = _trace(steps=4, cost_usd=0.51, latency_ms=101)
    results = run_checks(Expect(max_steps=3, max_cost_usd=0.5, max_latency_ms=100), trace)
    assert [r.passed for r in results] == [False, False, False]


def test_zero_budget_is_enforced():
    [check] = run_checks(Expect(max_steps=0), _trace(steps=1))
    assert not check.passed


def test_schema_non_json_output_fails_with_detail():
    [check] = run_checks(Expect(output_schema={"type": "object"}), _trace(output="plain text"))
    assert not check.passed
    assert "not valid JSON" in check.detail


def test_schema_type_mismatch_fails():
    schema = {"type": "object", "properties": {"total": {"type": "number"}}}
    [check] = run_checks(Expect(output_schema=schema), _trace(output='{"total": "42"}'))
    assert not check.passed


def test_schema_empty_output_fails():
    [check] = run_checks(Expect(output_schema={"type": "object"}), _trace(output=""))
    assert not check.passed


def test_check_order_is_stable():
    expect = Expect(
        tools=[ToolCallExpect(name="t")],
        contains=["a"],
        not_contains=["b"],
        output_schema={"type": "string"},
        max_cost_usd=1.0,
        max_latency_ms=1,
        max_steps=1,
    )
    names = [r.name for r in run_checks(expect, _trace(output='"a"', tool_calls=[ToolCallRecord(name="t")]))]
    assert names == [
        "tool:t",
        "contains:a",
        "not_contains:b",
        "output_schema",
        "budget:cost",
        "budget:latency",
        "budget:steps",
    ]
