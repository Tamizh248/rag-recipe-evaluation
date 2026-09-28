from app.core.constants import to_internal_strategy
from app.embeddings.sentence_transformer import EmbeddingModel
from app.models.search import SearchFilters
from app.retrieval.bm25 import rank_bm25
from app.vectorstore.chroma_store import ChromaStore, RetrievedChunk, UploadedRetrievedChunk

RRF_K = 60


class Retriever:
    """Single place that turns a question into embedded-query vector search.

    Both the search API and the chat/generation pipeline go through this
    class, so retrieval logic is never duplicated between them.
    """

    def __init__(self, store: ChromaStore, embedding_model: EmbeddingModel):
        self.store = store
        self.embedding_model = embedding_model

    def search(
        self,
        question: str,
        strategy: str,
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> list[RetrievedChunk]:
        """Hybrid BM25 + dense retrieval fused with reciprocal rank fusion."""
        return self._search(question, strategy, top_k, filters, hybrid=True)

    def search_dense(
        self,
        question: str,
        strategy: str,
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> list[RetrievedChunk]:
        """Dense-only baseline retained for repeatable evaluation."""
        return self._search(question, strategy, top_k, filters, hybrid=False)

    def _search(
        self,
        question: str,
        strategy: str,
        top_k: int,
        filters: SearchFilters | None,
        hybrid: bool,
    ) -> list[RetrievedChunk]:
        internal_strategy = to_internal_strategy(strategy)
        candidates = self.store.get_all(internal_strategy, filters)
        if not candidates:
            return []
        query_embedding = self.embedding_model.embed_query(question)
        dense_ranked = self.store.query(
            internal_strategy, query_embedding, len(candidates), filters
        )
        if not hybrid:
            return dense_ranked[:top_k]

        lexical_order = rank_bm25(question, [candidate.text for candidate in candidates])
        lexical_rank = {candidates[index].chunk_id: rank for rank, index in enumerate(lexical_order, start=1)}
        dense_rank = {chunk.chunk_id: rank for rank, chunk in enumerate(dense_ranked, start=1)}
        by_id = {chunk.chunk_id: chunk for chunk in candidates}
        fused = []
        for chunk_id, chunk in by_id.items():
            score = 1 / (RRF_K + dense_rank[chunk_id]) + 1 / (RRF_K + lexical_rank[chunk_id])
            fused.append(RetrievedChunk(chunk_id, chunk.text, chunk.metadata, score))
        return sorted(fused, key=lambda chunk: (-chunk.score, chunk.chunk_id))[:top_k]

    def search_uploaded(
        self, question: str, top_k: int = 5, doc_id: str | None = None
    ) -> list[UploadedRetrievedChunk]:
        """Hybrid BM25 + dense retrieval over the generic uploaded-documents
        collection, fused with the same RRF formula as `search` above."""
        candidates = self.store.get_all_uploaded(doc_id)
        if not candidates:
            return []
        query_embedding = self.embedding_model.embed_query(question)
        dense_ranked = self.store.query_uploaded(query_embedding, len(candidates), doc_id)

        lexical_order = rank_bm25(question, [candidate.text for candidate in candidates])
        lexical_rank = {candidates[index].chunk_id: rank for rank, index in enumerate(lexical_order, start=1)}
        dense_rank = {chunk.chunk_id: rank for rank, chunk in enumerate(dense_ranked, start=1)}
        by_id = {chunk.chunk_id: chunk for chunk in candidates}
        fused = []
        for chunk_id, chunk in by_id.items():
            score = 1 / (RRF_K + dense_rank[chunk_id]) + 1 / (RRF_K + lexical_rank[chunk_id])
            fused.append(UploadedRetrievedChunk(chunk_id, chunk.text, chunk.metadata, score))
        return sorted(fused, key=lambda chunk: (-chunk.score, chunk.chunk_id))[:top_k]
