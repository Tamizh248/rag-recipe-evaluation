from app.vectorstore.chroma_store import RetrievedChunk

GROUNDING_INSTRUCTIONS = """You are a recipe assistant. Answer the question using ONLY the supplied context below.

Rules:
- Use ONLY the supplied context. Do not use external knowledge.
- Do not guess. Do not invent quantities. Do not infer missing nutritional information.
- Every factual claim in your answer must have a citation.
- Every citation must refer to a real chunk_id from the context below.
- If the context does not contain enough information to answer the question, refuse to answer.

Respond with ONLY a single JSON object, no other text, matching exactly this schema:
{"answerable": true or false, "answer": "<answer text>", "citations": [{"chunk_id": "<chunk_id from context>"}]}

If you cannot answer from the context, respond with exactly:
{"answerable": false, "answer": "I cannot answer this from the provided recipes.", "citations": []}
"""


def build_grounding_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_blocks = [f"[chunk_id: {c.chunk_id}]\n{c.text}" for c in chunks]
    context = "\n\n---\n\n".join(context_blocks)
    return (
        f"{GROUNDING_INSTRUCTIONS}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{question}\n"
    )
