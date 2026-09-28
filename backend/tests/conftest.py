import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from app.chunking.current_chunker import CurrentChunker
from app.chunking.structure_aware_chunker import StructureAwareChunker
from app.core.config import get_settings
from app.core.tracing import TraceLogger
from app.embeddings.sentence_transformer import EmbeddingModel
from app.generation.llm import LocalExtractiveProvider
from app.retrieval.retriever import Retriever
from app.services.chat_service import ChatService
from app.services.ingestion_service import ingest_recipes
from app.vectorstore.chroma_store import ChromaStore


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def embedding_model(settings):
    return EmbeddingModel(settings.embedding_model)


@pytest.fixture(scope="session")
def store(tmp_path_factory, settings, embedding_model):
    """Real ChromaDB instance in an isolated temp directory, ingested with
    both chunking strategies once per test session (not the production
    ./data/chroma directory).
    """
    chroma_dir = tmp_path_factory.mktemp("chroma_test")
    test_store = ChromaStore(chroma_dir)

    current_chunker = CurrentChunker(settings.current_chunk_size, settings.current_chunk_overlap)
    structure_chunker = StructureAwareChunker()
    ingest_recipes(settings.recipes_dir, current_chunker, embedding_model, test_store)
    ingest_recipes(settings.recipes_dir, structure_chunker, embedding_model, test_store)

    return test_store


@pytest.fixture(scope="session")
def retriever(store, embedding_model):
    return Retriever(store, embedding_model)


@pytest.fixture(scope="session")
def chat_service(retriever, settings, tmp_path_factory):
    # A test-local trace log, never the production evaluation/week5/traces.jsonl -
    # otherwise every pytest run would mix synthetic test traffic into the real
    # Week-5 trace sample.
    trace_logger = TraceLogger(tmp_path_factory.mktemp("traces") / "test_traces.jsonl")
    return ChatService(
        retriever,
        LocalExtractiveProvider(),
        top_k=settings.top_k,
        model_provider="local",
        model_name="local-extractive",
        trace_logger=trace_logger,
    )
