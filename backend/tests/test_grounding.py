from app.generation.grounding import enforce_refusal_policy, has_lexical_support
from app.models.chat import Citation, GroundedAnswer
from app.vectorstore.chroma_store import RetrievedChunk
from app.models.chunk import ChunkMetadata


def _fake_chunk(chunk_id: str, text: str) -> RetrievedChunk:
    metadata = ChunkMetadata(
        chunk_id=chunk_id,
        source_file="x.txt",
        recipe_id="x",
        cuisine="bread",
        dietary_tags=["vegan"],
        section="ingredients",
        chunking_strategy="structure_aware",
    )
    return RetrievedChunk(chunk_id=chunk_id, text=text, metadata=metadata, score=0.9)


def test_has_lexical_support_true_for_on_topic_question():
    chunks = [_fake_chunk("c1", "Fine Sea Salt | 20g | 2%")]
    assert has_lexical_support("How much salt is used?", chunks) is True


def test_has_lexical_support_false_for_absent_nutrition_fact():
    chunks = [_fake_chunk("c1", "Recipe: Sourdough Country Loaf\nFine Sea Salt | 20g | 2%")]
    assert has_lexical_support("What is the protein content per serving?", chunks) is False


def test_has_lexical_support_false_with_no_chunks():
    assert has_lexical_support("How much salt is used?", []) is False


def test_enforce_refusal_policy_rejects_answer_with_no_citations():
    answer = GroundedAnswer(answerable=True, answer="The salt is 20g.", citations=[])
    result = enforce_refusal_policy(answer, retrieved_chunk_ids={"c1"})
    assert result.answerable is False


def test_enforce_refusal_policy_rejects_citation_outside_retrieved_set():
    answer = GroundedAnswer(
        answerable=True, answer="The salt is 20g.", citations=[Citation(chunk_id="not_retrieved")]
    )
    result = enforce_refusal_policy(answer, retrieved_chunk_ids={"c1"})
    assert result.answerable is False


def test_enforce_refusal_policy_passes_through_valid_answer():
    answer = GroundedAnswer(
        answerable=True, answer="The salt is 20g.", citations=[Citation(chunk_id="c1")]
    )
    result = enforce_refusal_policy(answer, retrieved_chunk_ids={"c1"})
    assert result.answerable is True
    assert result.citations[0].chunk_id == "c1"


def test_chat_service_refuses_unanswerable_question(chat_service):
    response = chat_service.answer(
        "What is the protein content per serving of the Sourdough Country Loaf?",
        strategy="structure-aware",
    )
    assert response.refused is True
    assert response.citations == []


def test_chat_service_answers_answerable_question_with_citation(chat_service):
    response = chat_service.answer(
        "What vessel is used to bake the Sourdough Country Loaf?", strategy="structure-aware"
    )
    assert response.refused is False
    assert len(response.citations) >= 1
    assert response.citations[0].chunk_id in response.retrieved_chunk_ids
