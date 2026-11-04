from __future__ import annotations

import json
import os

import structlog
from openai import AsyncOpenAI

from app.core.pricing import cost_usd
from app.schemas import AgentTrace, EvalCase

logger = structlog.get_logger(__name__)

# Judge prompt is version-locked. Changing it = new version + re-validation against the
# meta-set of human-labeled cases (see ADR-001). Do NOT edit silently: judge drift makes
# every downstream eval result incomparable across runs.
JUDGE_PROMPT_VERSION = "v1"
_JUDGE_SYSTEM = """You are a strict evaluator of an AI agent's response.
You are given: the task the agent was asked to do, a behavior contract describing what a
correct response must satisfy, and the agent's actual final output.

Score how well the output satisfies the contract. Be skeptical. A fluent answer that does
not satisfy the contract scores low. Judge behavior and faithfulness, not writing style.

Return ONLY JSON: {"score": <float 0..1>, "confidence": <float 0..1>, "reason": "<short>"}
score = how well the contract is met. confidence = how sure you are in this judgment."""


class JudgeError(ValueError):
    pass


def _unit_interval(data: dict, key: str) -> float:
    value = data.get(key, 0.0)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise JudgeError(f"judge field '{key}' is not numeric: {value!r}")
    try:
        number = float(value)
    except ValueError as exc:
        raise JudgeError(f"judge field '{key}' is not numeric: {value!r}") from exc
    if not 0.0 <= number <= 1.0:
        raise JudgeError(f"judge field '{key}' out of range 0..1: {number}")
    return number


def parse_verdict(content: str | None) -> tuple[float, float, str]:
    if not content:
        raise JudgeError("judge returned empty content")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise JudgeError(f"judge returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise JudgeError("judge JSON is not an object")
    return _unit_interval(data, "score"), _unit_interval(data, "confidence"), str(data.get("reason", ""))


class Judge:
    def __init__(self, model: str = "gpt-4o-mini", threshold: float = 0.7, min_confidence: float = 0.6) -> None:
        self.model = model
        self.threshold = threshold
        self.min_confidence = min_confidence
        self._client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def score(self, case: EvalCase, trace: AgentTrace) -> tuple[float, float, float]:
        user = (
            f"TASK:\n{case.input}\n\n"
            f"BEHAVIOR CONTRACT:\n{case.expect.judge}\n\n"
            f"AGENT OUTPUT:\n{trace.output}"
        )
        resp = await self._client.chat.completions.create(
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        score, confidence, reason = parse_verdict(resp.choices[0].message.content)

        usage = resp.usage
        judge_cost = cost_usd(self.model, usage.prompt_tokens, usage.completion_tokens) if usage else 0.0

        logger.info(
            "judge_scored",
            case=case.id,
            score=score,
            confidence=confidence,
            version=JUDGE_PROMPT_VERSION,
            reason=reason,
        )
        return score, confidence, judge_cost

    def passed(self, score: float, confidence: float) -> bool:
        # Low-confidence judgments do not pass on their own. A confident low score fails;
        # a low-confidence score is treated as a fail so humans review it (conservative).
        return confidence >= self.min_confidence and score >= self.threshold
