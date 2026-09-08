from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service
from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)) -> ChatResponse:
    return service.answer(request.question, strategy=request.strategy, filters=request.filters)
