import re

# Canonical set of dietary tags used across the recipe corpus. Each tag is
# stored in ChromaDB as its own boolean metadata flag (dietary_<slug>) so
# that filtering happens as a real vector-database `where` clause rather
# than post-retrieval Python filtering.
KNOWN_DIETARY_TAGS = [
    "vegan",
    "vegetarian",
    "contains-dairy",
    "contains-eggs",
    "contains-nuts",
]


def dietary_flag_key(tag: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", tag.lower()).strip("_")
    return f"dietary_{slug}"


# API-facing strategy names use a hyphen ("structure-aware"); internally
# (chunk metadata, Chroma collection lookups) we use an underscore
# ("structure_aware") since it must also be a valid Python identifier/enum
# value. This is the single place that translation happens.
STRATEGY_API_TO_INTERNAL = {
    "current": "current",
    "structure-aware": "structure_aware",
}
STRATEGY_INTERNAL_TO_API = {v: k for k, v in STRATEGY_API_TO_INTERNAL.items()}


def to_internal_strategy(api_strategy: str) -> str:
    try:
        return STRATEGY_API_TO_INTERNAL[api_strategy]
    except KeyError:
        raise ValueError(f"Unknown strategy: {api_strategy}") from None
