from __future__ import annotations

from pydantic import BaseModel, Field


class ToolCallExpect(BaseModel):
    name: str
    args_subset: dict | None = None


class Expect(BaseModel):
    tools: list[ToolCallExpect] = Field(default_factory=list)
    contains: list[str] = Field(default_factory=list)
    not_contains: list[str] = Field(default_factory=list)
    output_schema: dict | None = None
    judge: str | None = None
    max_cost_usd: float | None = None
    max_latency_ms: int | None = None
    max_steps: int | None = None


class EvalCase(BaseModel):
    id: str
    input: str
    context: dict | None = None
    expect: Expect = Field(default_factory=Expect)


class ToolCallRecord(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class AgentTrace(BaseModel):
    output: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    steps: int = 1
    cost_usd: float = 0.0
    latency_ms: int = 0


class CheckResult(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class CaseResult(BaseModel):
    case_id: str
    passed: bool
    checks: list[CheckResult] = Field(default_factory=list)
    trace: AgentTrace
    judge_score: float | None = None
    judge_confidence: float | None = None
    error: str | None = None


class RunReport(BaseModel):
    dataset: str
    agent: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    total_cost_usd: float
    results: list[CaseResult] = Field(default_factory=list)
