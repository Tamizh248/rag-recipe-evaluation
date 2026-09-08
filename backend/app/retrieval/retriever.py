from app.core.constants import to_internal_strategy
from app.embeddings.sentence_transformer import EmbeddingModel
from app.models.search import SearchFilters
from app.vectorstore.chroma_store import ChromaStore, RetrievedChunk


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
        internal_strategy = to_internal_strategy(strategy)
        query_embedding = self.embedding_model.embed_query(question)
        return self.store.query(internal_strategy, query_embedding, top_k, filters)
