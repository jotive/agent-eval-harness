import pytest

from app.core.judge import JudgeError, parse_verdict
from app.schemas import AgentTrace, EvalCase, Expect

CASE = EvalCase(id="c1", input="question", expect=Expect(judge="contract"))
TRACE = AgentTrace(output="answer")


@pytest.mark.parametrize(
    "content",
    [
        None,
        "",
        "not json",
        "[1, 2]",
        '"text"',
        '{"score": "high", "confidence": 0.9}',
        '{"score": null, "confidence": 0.9}',
        '{"score": [0.5], "confidence": 0.9}',
        '{"score": true, "confidence": 0.9}',
        '{"score": 1.5, "confidence": 0.9}',
        '{"score": 0.5, "confidence": -0.1}',
        '{"score": NaN, "confidence": 0.9}',
    ],
)
def test_parse_verdict_rejects_malformed(content):
    with pytest.raises(JudgeError):
        parse_verdict(content)


def test_parse_verdict_missing_fields_default_to_zero():
    assert parse_verdict("{}") == (0.0, 0.0, "")


def test_parse_verdict_accepts_numeric_strings_and_bounds():
    assert parse_verdict('{"score": "0.8", "confidence": 1, "reason": "ok"}') == (0.8, 1.0, "ok")
    assert parse_verdict('{"score": 0, "confidence": 0}') == (0.0, 0.0, "")


async def test_score_returns_verdict_and_cost(make_judge):
    judge = make_judge(['{"score": 0.9, "confidence": 0.8, "reason": "good"}'], model="gpt-4o-mini")
    score, confidence, cost = await judge.score(CASE, TRACE)
    assert (score, confidence) == (0.9, 0.8)
    assert cost == pytest.approx((100 * 0.15 + 20 * 0.60) / 1_000_000)


async def test_score_raises_on_malformed_output(make_judge):
    judge = make_judge(["{broken"])
    with pytest.raises(JudgeError):
        await judge.score(CASE, TRACE)


async def test_score_propagates_api_failure(make_judge):
    judge = make_judge(error=RuntimeError("rate limited"))
    with pytest.raises(RuntimeError, match="rate limited"):
        await judge.score(CASE, TRACE)


@pytest.mark.parametrize(
    ("score", "confidence", "expected"),
    [
        (0.7, 0.6, True),
        (1.0, 1.0, True),
        (0.69, 1.0, False),
        (1.0, 0.59, False),
        (0.0, 0.0, False),
        (0.7, 0.0, False),
    ],
)
def test_passed_thresholds(make_judge, score, confidence, expected):
    judge = make_judge(threshold=0.7, min_confidence=0.6)
    assert judge.passed(score, confidence) is expected


def test_passed_respects_custom_thresholds(make_judge):
    judge = make_judge(threshold=0.9, min_confidence=0.9)
    assert not judge.passed(0.89, 0.95)
    assert judge.passed(0.9, 0.9)
