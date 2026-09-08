from pydantic import BaseModel, Field

from app.models.search import Strategy, SearchFilters


class ChatRequest(BaseModel):
    question: str
    strategy: Strategy = "structure-aware"
    filters: SearchFilters = Field(default_factory=SearchFilters)


class Citation(BaseModel):
    chunk_id: str


class GroundedAnswer(BaseModel):
    """Structured output the LLM must produce, validated before it reaches the API layer."""

    answerable: bool
    answer: str
    citations: list[Citation] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    refused: bool
    citations: list[Citation]
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
