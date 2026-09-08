from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingModel:
    """Thin wrapper around a Sentence Transformer model.

    Centralizing embedding calls here (rather than calling
    SentenceTransformer directly from chunking/retrieval code) guarantees
    ingestion and retrieval always use the exact same model and encoding
    settings, which is required to keep the current-vs-structure-aware
    chunking experiment isolated to chunking alone.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        logger.info("Loading embedding model %s", model_name)
        self._model = SentenceTransformer(model_name)

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


@lru_cache
def get_embedding_model() -> EmbeddingModel:
    settings = get_settings()
    return EmbeddingModel(settings.embedding_model)
