from __future__ import annotations

import importlib
import json
import os
import time
from typing import Protocol, runtime_checkable

import structlog
from openai import AsyncOpenAI

from app.core.pricing import cost_usd
from app.schemas import AgentTrace, EvalCase, ToolCallRecord

logger = structlog.get_logger(__name__)


@runtime_checkable
class AgentUnderTest(Protocol):
    async def __call__(self, case: EvalCase) -> AgentTrace: ...


def load_agent(dotted_path: str) -> AgentUnderTest:
    # "package.module:factory" -> import module, call factory(), return the callable agent.
    module_name, _, attr = dotted_path.partition(":")
    if not attr:
        raise ValueError("agent path must be 'module:factory' (got no ':')")
    module = importlib.import_module(module_name)
    factory = getattr(module, attr)
    agent = factory()
    if not callable(agent):
        raise TypeError(f"{dotted_path} did not return a callable agent")
    return agent


# --- Reference agent under test ----------------------------------------------
# Minimal tool-calling agent so the harness runs end-to-end out of the box.
# Swap for your real agent via --agent your_pkg:make_agent.

_DEMO_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search the internal document corpus for a query.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    }
]


class DemoAgent:
    def __init__(self, model: str = "gpt-4o-mini", max_steps: int = 4) -> None:
        self.model = model
        self.max_steps = max_steps
        self._client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    async def __call__(self, case: EvalCase) -> AgentTrace:
        messages = [{"role": "user", "content": case.input}]
        tool_calls: list[ToolCallRecord] = []
        cost = 0.0
        steps = 0
        start = time.monotonic()

        while steps < self.max_steps:
            steps += 1
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=_DEMO_TOOLS,
                temperature=0.0,
            )
            if resp.usage:
                cost += cost_usd(self.model, resp.usage.prompt_tokens, resp.usage.completion_tokens)

            choice = resp.choices[0].message
            if not choice.tool_calls:
                latency_ms = int((time.monotonic() - start) * 1000)
                return AgentTrace(
                    output=choice.content or "",
                    tool_calls=tool_calls,
                    steps=steps,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                )

            messages.append(choice.model_dump(exclude_none=True))
            for call in choice.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                tool_calls.append(ToolCallRecord(name=call.function.name, args=args))
                result = _run_demo_tool(call.function.name, args)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        latency_ms = int((time.monotonic() - start) * 1000)
        return AgentTrace(
            output="<<max steps reached without final answer>>",
            tool_calls=tool_calls,
            steps=steps,
            cost_usd=cost,
            latency_ms=latency_ms,
        )


def _run_demo_tool(name: str, args: dict) -> str:
    if name == "search_docs":
        return f"[stub] no live corpus. echoing query: {args.get('query', '')}"
    return f"[stub] unknown tool {name}"


def make_demo_agent() -> DemoAgent:
    return DemoAgent()
