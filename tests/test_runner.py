import pytest

from app.core.runner import run_dataset
from app.schemas import AgentTrace, EvalCase, Expect

JUDGED = '{"score": 0.9, "confidence": 0.9, "reason": "ok"}'


async def _agent(case):
    return AgentTrace(output=f"answer to {case.input}", cost_usd=0.01)


def _cases(count=3, **expect):
    return [EvalCase(id=f"c{i}", input=f"q{i}", expect=Expect(judge="contract", **expect)) for i in range(count)]


async def _run(cases, judge, agent=_agent):
    return await run_dataset(cases, agent, "d", "a", judge=judge)


async def test_judge_pass_marks_case_passed(make_judge):
    report = await _run(_cases(1), make_judge([JUDGED]))
    [result] = report.results
    assert result.passed
    assert result.judge_score == 0.9
    assert result.judge_confidence == 0.9
    assert result.trace.cost_usd > 0.01


async def test_low_score_fails(make_judge):
    report = await _run(_cases(1), make_judge(['{"score": 0.2, "confidence": 0.9}']))
    assert not report.results[0].passed


async def test_low_confidence_fails(make_judge):
    report = await _run(_cases(1), make_judge(['{"score": 0.95, "confidence": 0.3}']))
    assert not report.results[0].passed


async def test_malformed_judge_output_fails_case_without_crashing_run(make_judge):
    report = await _run(_cases(2), make_judge(["garbage"]))
    assert report.total == 2
    assert report.failed == 2
    assert all("judge failed" in r.error for r in report.results)


async def test_judge_api_error_fails_case_without_crashing_run(make_judge):
    report = await _run(_cases(2), make_judge(error=RuntimeError("boom")))
    assert report.failed == 2
    assert "boom" in report.results[0].error


async def test_judge_failure_keeps_deterministic_checks(make_judge):
    cases = _cases(1, contains=["answer"])
    report = await _run(cases, make_judge(error=RuntimeError("boom")))
    assert [c.name for c in report.results[0].checks] == ["contains:answer"]


async def test_deterministic_failure_fails_even_with_perfect_judge(make_judge):
    report = await _run(_cases(1, contains=["absent"]), make_judge([JUDGED]))
    result = report.results[0]
    assert not result.passed
    assert result.judge_score == 0.9


async def test_judge_skipped_without_judge_instance():
    report = await _run(_cases(1), None)
    result = report.results[0]
    assert result.passed
    assert result.judge_score is None


async def test_agent_crash_fails_case_only(make_judge):
    async def flaky(case):
        if case.id == "c1":
            raise RuntimeError("agent down")
        return AgentTrace(output="ok")

    report = await _run(_cases(3), make_judge([JUDGED]), agent=flaky)
    by_id = {r.case_id: r for r in report.results}
    assert not by_id["c1"].passed
    assert by_id["c1"].error == "agent down"
    assert by_id["c0"].passed and by_id["c2"].passed


async def test_empty_dataset_has_zero_pass_rate():
    report = await _run([], None)
    assert (report.total, report.passed, report.failed, report.pass_rate) == (0, 0, 0, 0.0)


async def test_all_pass_rate_is_one(make_judge):
    report = await _run(_cases(4), make_judge([JUDGED]))
    assert report.pass_rate == 1.0


async def test_partial_pass_rate(make_judge):
    judge = make_judge([JUDGED, '{"score": 0.1, "confidence": 0.9}'])
    report = await run_dataset(_cases(2), _agent, "d", "a", judge=judge, concurrency=1)
    assert report.passed == 1
    assert report.pass_rate == 0.5


async def test_total_cost_sums_agent_and_judge(make_judge):
    report = await _run(_cases(2), make_judge([JUDGED]))
    assert report.total_cost_usd == pytest.approx(sum(r.trace.cost_usd for r in report.results))


@pytest.mark.parametrize("concurrency", [1, 2, 8])
async def test_scoring_is_deterministic_with_stubbed_judge(make_judge, concurrency):
    cases = _cases(6, contains=["answer"])
    first = await run_dataset(cases, _agent, "d", "a", judge=make_judge([JUDGED]), concurrency=concurrency)
    second = await run_dataset(cases, _agent, "d", "a", judge=make_judge([JUDGED]), concurrency=concurrency)
    assert first.model_dump() == second.model_dump()


async def test_result_order_matches_input_order(make_judge):
    report = await _run(_cases(5), make_judge([JUDGED]))
    assert [r.case_id for r in report.results] == [f"c{i}" for i in range(5)]
