from __future__ import annotations

# USD per 1M tokens. APPROXIMATE — verify against provider pricing before trusting cost gates.
# Source: OpenAI pricing page. Snapshot 2026-06-06. [verify periodically]
_PRICING: dict[str, tuple[float, float]] = {
    # model: (input_per_1m, output_per_1m)
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "text-embedding-3-small": (0.02, 0.0),
}


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    if model not in _PRICING:
        return 0.0
    in_rate, out_rate = _PRICING[model]
    return (prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000
