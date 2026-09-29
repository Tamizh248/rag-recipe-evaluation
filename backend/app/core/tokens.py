"""No real tokenizer ships with this project (no torch/tiktoken generation
stack), so token counts everywhere in the agent (Week 7's cost/token
budget and race numbers) use a disclosed, approximate estimator: ~4
characters per token, the same rule of thumb Anthropic and OpenAI both
publish for rough English-text estimates. It is not exact, but it is
consistent across every call in this project, which is what the before/
after and agent-vs-workflow comparisons need.
"""


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)
