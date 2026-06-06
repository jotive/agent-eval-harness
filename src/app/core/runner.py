from __future__ import annotations

import asyncio

import structlog

from app.core.agent import AgentUnderTest
from app.core.checks import run_checks
from app.core.judge import Judge
from app.schemas import CaseResult, EvalCase, RunReport

logger = structlog.get_logger(__name__)


async def _run_case(case: EvalCase, agent: AgentUnderTest, judge: Judge | None) -> CaseResult:
    try:
        trace = await agent(case)
    except Exception as exc:  # agent crash = failed case, not crashed run
        logger.warning("agent_error", case=case.id, error=str(exc))
        from app.schemas import AgentTrace

        return CaseResult(case_id=case.id, passed=False, trace=AgentTrace(output=""), error=str(exc))

    checks = run_checks(case.expect, trace)
    deterministic_ok = all(c.passed for c in checks)

    judge_score = judge_conf = None
    judge_ok = True
    if case.expect.judge and judge is not None:
        judge_score, judge_conf, judge_cost = await judge.score(case, trace)
        trace.cost_usd += judge_cost
        judge_ok = judge.passed(judge_score, judge_conf)

    passed = deterministic_ok and judge_ok
    return CaseResult(
        case_id=case.id,
        passed=passed,
        checks=checks,
        trace=trace,
        judge_score=judge_score,
        judge_confidence=judge_conf,
    )


async def run_dataset(
    cases: list[EvalCase],
    agent: AgentUnderTest,
    dataset_name: str,
    agent_name: str,
    judge: Judge | None = None,
    concurrency: int = 4,
) -> RunReport:
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(case: EvalCase) -> CaseResult:
        async with sem:
            return await _run_case(case, agent, judge)

    results = await asyncio.gather(*(_bounded(c) for c in cases))

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    return RunReport(
        dataset=dataset_name,
        agent=agent_name,
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=passed / total if total else 0.0,
        total_cost_usd=sum(r.trace.cost_usd for r in results),
        results=list(results),
    )
