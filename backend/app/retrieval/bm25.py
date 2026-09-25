"""Small dependency-free BM25 implementation for the recipe corpus."""

from collections import Counter
import math
import re


TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def rank_bm25(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[int]:
    """Return document indexes ordered by BM25 score, with stable tie breaks."""
    if not documents:
        return []

    tokenized_documents = [tokenize(document) for document in documents]
    document_frequencies: Counter[str] = Counter()
    for document in tokenized_documents:
        document_frequencies.update(set(document))

    average_length = sum(len(document) for document in tokenized_documents) / len(documents)
    query_terms = set(tokenize(query))
    scores: list[float] = []

    for document in tokenized_documents:
        term_frequencies = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = term_frequencies[term]
            if not frequency:
                continue
            inverse_document_frequency = math.log(
                1 + (len(documents) - document_frequencies[term] + 0.5)
                / (document_frequencies[term] + 0.5)
            )
            denominator = frequency + k1 * (1 - b + b * len(document) / average_length)
            score += inverse_document_frequency * frequency * (k1 + 1) / denominator
        scores.append(score)

    return sorted(range(len(documents)), key=lambda index: (-scores[index], index))
