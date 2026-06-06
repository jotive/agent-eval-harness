from __future__ import annotations

from pathlib import Path

import structlog
import yaml

from app.schemas import EvalCase

logger = structlog.get_logger(__name__)


def load_dataset(path: str | Path) -> list[EvalCase]:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    if isinstance(raw, dict):
        raw = raw.get("cases", [])

    cases = [EvalCase.model_validate(item) for item in raw]

    seen: set[str] = set()
    for case in cases:
        if case.id in seen:
            raise ValueError(f"duplicate case id in dataset: {case.id}")
        seen.add(case.id)

    logger.info("dataset_loaded", path=str(path), cases=len(cases))
    return cases
