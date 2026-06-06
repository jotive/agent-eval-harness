from __future__ import annotations

import asyncio

import typer

from app.core.agent import load_agent
from app.core.dataset import load_dataset
from app.core.judge import Judge
from app.core.report import console, detect_regressions, load_report, print_report, save_report
from app.core.runner import run_dataset

app = typer.Typer(add_completion=False, help="Evaluation harness for LLM agents.")


@app.callback()
def _main() -> None:
    # Presence of a callback keeps `run` as an explicit subcommand (`eval run ...`)
    # instead of collapsing into the root command.
    ...


@app.command()
def run(
    dataset: str = typer.Option(..., "--dataset", "-d", help="Path to YAML dataset."),
    agent: str = typer.Option("app.core.agent:make_demo_agent", "--agent", "-a", help="Agent factory 'module:factory'."),
    out: str = typer.Option("report.json", "--out", "-o", help="Where to write the run report JSON."),
    baseline: str | None = typer.Option(None, "--baseline", "-b", help="Prior report JSON to compare against."),
    judge_model: str = typer.Option("gpt-4o-mini", "--judge-model"),
    judge_threshold: float = typer.Option(0.7, "--judge-threshold"),
    pass_rate_drop: float = typer.Option(0.0, "--max-drop", help="Allowed pass-rate drop vs baseline before failing CI."),
    concurrency: int = typer.Option(4, "--concurrency", "-c"),
) -> None:
    cases = load_dataset(dataset)
    agent_callable = load_agent(agent)
    judge = Judge(model=judge_model, threshold=judge_threshold)

    report = asyncio.run(
        run_dataset(cases, agent_callable, dataset_name=dataset, agent_name=agent, judge=judge, concurrency=concurrency)
    )

    print_report(report)
    save_report(report, out)
    console.print(f"report written: {out}")

    exit_code = 0 if report.failed == 0 else 1

    if baseline:
        regressions = detect_regressions(load_report(baseline), report, pass_rate_drop=pass_rate_drop)
        if regressions:
            console.print("[red]REGRESSIONS:[/]")
            for r in regressions:
                console.print(f"  - {r}")
            exit_code = 1
        else:
            console.print("[green]no regressions vs baseline[/]")

    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
