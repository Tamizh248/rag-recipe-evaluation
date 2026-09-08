from app.models.search import SearchRequest, SearchResponse, SearchResultItem
from app.retrieval.retriever import Retriever


class SearchService:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever

    def search(self, request: SearchRequest) -> SearchResponse:
        retrieved = self.retriever.search(
            request.question,
            strategy=request.strategy,
            top_k=request.top_k,
            filters=request.filters,
        )
        results = [
            SearchResultItem(
                chunk_id=r.chunk_id,
                score=r.score,
                recipe_id=r.metadata.recipe_id,
                section=r.metadata.section,
                source_file=r.metadata.source_file,
                text=r.text,
                metadata=r.metadata,
            )
            for r in retrieved
        ]
        return SearchResponse(results=results)
