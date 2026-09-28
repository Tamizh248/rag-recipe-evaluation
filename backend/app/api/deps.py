from functools import lru_cache

from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.generation.llm import get_llm_provider
from app.retrieval.retriever import Retriever
from app.services.chat_service import ChatService
from app.services.search_service import SearchService
from app.services.uploaded_chat_service import UploadedChatService
from app.vectorstore.chroma_store import ChromaStore


@lru_cache
def get_store() -> ChromaStore:
    return ChromaStore(get_settings().chroma_persist_path)


@lru_cache
def get_retriever() -> Retriever:
    return Retriever(get_store(), get_embedding_model())


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(get_retriever())


@lru_cache
def get_chat_service() -> ChatService:
    settings = get_settings()
    provider = get_llm_provider(settings.llm_provider, settings.llm_api_key, settings.llm_model)
    return ChatService(
        get_retriever(),
        provider,
        top_k=settings.top_k,
        model_provider=settings.llm_provider,
        model_name=settings.llm_model,
    )


@lru_cache
def get_uploaded_chat_service() -> UploadedChatService:
    settings = get_settings()
    provider = get_llm_provider(settings.llm_provider, settings.llm_api_key, settings.llm_model)
    return UploadedChatService(get_retriever(), provider, top_k=settings.top_k)
