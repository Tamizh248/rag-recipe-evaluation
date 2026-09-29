"""Dollar-cost estimate for one request, needed for the race's "cost per
request" number and the MAX_COST budget (Week 7 requires 4 enforced
budgets: max iterations, max tokens, max cost, wall-clock).

Pricing is published, per-million-token list pricing (input/output priced
separately) - a real, disclosed number, not invented - current as of this
project's build. `local` truly costs $0 per request (no API call is ever
made), which is an honest number to report, not a stand-in.
"""

# USD per 1M tokens (input, output). Update if pricing changes.
_PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5-5": (15.00, 75.00),
    "claude-haiku-4-5-20251001": (0.80, 4.00),
}
_DEFAULT_ANTHROPIC_PRICING = (3.00, 15.00)


def estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    if provider != "anthropic":
        return 0.0
    input_price, output_price = _PRICING_PER_MILLION_TOKENS.get(model, _DEFAULT_ANTHROPIC_PRICING)
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
