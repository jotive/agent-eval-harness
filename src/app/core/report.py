from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from app.schemas import RunReport

console = Console()


def save_report(report: RunReport, path: str | Path) -> None:
    Path(path).write_text(report.model_dump_json(indent=2), encoding="utf-8")


def load_report(path: str | Path) -> RunReport:
    return RunReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def print_report(report: RunReport) -> None:
    table = Table(title=f"eval: {report.dataset} vs {report.agent}")
    table.add_column("case")
    table.add_column("result")
    table.add_column("judge")
    table.add_column("failed checks")

    for r in report.results:
        status = "[green]PASS[/]" if r.passed else "[red]FAIL[/]"
        judge = f"{r.judge_score:.2f}@{r.judge_confidence:.2f}" if r.judge_score is not None else "-"
        failed = ", ".join(c.name for c in r.checks if not c.passed) or (r.error or "")
        table.add_row(r.case_id, status, judge, failed)

    console.print(table)
    console.print(
        f"pass {report.passed}/{report.total} "
        f"({report.pass_rate:.0%})  cost ${report.total_cost_usd:.4f}"
    )


def detect_regressions(baseline: RunReport, current: RunReport, pass_rate_drop: float = 0.0) -> list[str]:
    # A regression is a case that passed in baseline and now fails, OR an overall
    # pass-rate drop beyond the allowed threshold.
    base_by_id = {r.case_id: r for r in baseline.results}
    regressions: list[str] = []

    for r in current.results:
        prior = base_by_id.get(r.case_id)
        if prior is not None and prior.passed and not r.passed:
            failed = ", ".join(c.name for c in r.checks if not c.passed) or (r.error or "judge")
            regressions.append(f"{r.case_id}: passed before, now fails ({failed})")

    drop = baseline.pass_rate - current.pass_rate
    if drop > pass_rate_drop:
        regressions.append(f"pass_rate dropped {baseline.pass_rate:.0%} -> {current.pass_rate:.0%} (max allowed drop {pass_rate_drop:.0%})")

    return regressions
