from app.core.report import detect_regressions
from app.schemas import AgentTrace, CaseResult, RunReport


def _report(pairs):
    results = [
        CaseResult(case_id=cid, passed=passed, trace=AgentTrace(output=""))
        for cid, passed in pairs
    ]
    passed = sum(1 for _, p in pairs if p)
    total = len(pairs)
    return RunReport(
        dataset="d", agent="a", total=total, passed=passed, failed=total - passed,
        pass_rate=passed / total if total else 0.0, total_cost_usd=0.0, results=results,
    )


def test_detects_case_that_now_fails():
    base = _report([("c1", True), ("c2", True)])
    curr = _report([("c1", True), ("c2", False)])
    regs = detect_regressions(base, curr)
    assert any("c2" in r for r in regs)


def test_no_regression_when_stable():
    base = _report([("c1", True), ("c2", True)])
    curr = _report([("c1", True), ("c2", True)])
    assert detect_regressions(base, curr) == []


def test_new_passing_case_is_not_regression():
    base = _report([("c1", True)])
    curr = _report([("c1", True), ("c2", True)])
    assert detect_regressions(base, curr) == []


def test_pass_rate_drop_flagged():
    base = _report([("c1", True), ("c2", True)])
    curr = _report([("c1", False), ("c2", False)])
    regs = detect_regressions(base, curr, pass_rate_drop=0.1)
    assert any("pass_rate" in r for r in regs)
