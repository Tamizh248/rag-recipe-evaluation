from fastapi import APIRouter, Depends

from app.api.deps import get_search_service
from app.models.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest, service: SearchService = Depends(get_search_service)) -> SearchResponse:
    return service.search(request)
