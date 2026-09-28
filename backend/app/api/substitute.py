from fastapi import APIRouter, Depends

from app.api.deps import get_substitution_service
from app.models.substitution import SubstitutionRequest, SubstitutionResponse
from app.substitution.service import SubstitutionService

router = APIRouter()


@router.post("/api/substitute", response_model=SubstitutionResponse)
def substitute(
    request: SubstitutionRequest, service: SubstitutionService = Depends(get_substitution_service)
) -> SubstitutionResponse:
    return service.substitute(request.recipe_id, request.ingredient, request.diet)
