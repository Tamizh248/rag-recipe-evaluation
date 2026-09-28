from pydantic import BaseModel, Field

from app.models.chat import Citation


class SubstitutionRequest(BaseModel):
    recipe_id: str
    ingredient: str
    diet: str


class SubstitutionAnswer(BaseModel):
    """Structured output the LLM must produce, validated before it reaches
    the API layer - same discipline as GroundedAnswer in models/chat.py."""

    answerable: bool
    answer: str
    substitute_ingredient: str | None = None
    adapted_ingredients: list[str] = Field(default_factory=list)
    adapted_method: str = ""
    oven: str = ""
    servings: str = ""
    allergens: str = ""
    citations: list[Citation] = Field(default_factory=list)


class SubstitutionResponse(BaseModel):
    answer: str
    refused: bool
    substitute_ingredient: str | None
    adapted_ingredients: list[str]
    adapted_method: str
    oven: str
    servings: str
    allergens: str
    citations: list[Citation]
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
