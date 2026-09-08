from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",

    )
    # LLM
    llm_provider: str = "local"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-5"

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"

    # Vector store
    chroma_persist_directory: str = "./data/chroma"

    # Retrieval
    top_k: int = 5

    # Current (baseline) chunker
    current_chunk_size: int = 250
    current_chunk_overlap: int = 50

    # CORS
    cors_origins: str = "http://localhost:4200"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def chroma_persist_path(self) -> Path:
        path = Path(self.chroma_persist_directory)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path

    @property
    def recipes_dir(self) -> Path:
        return BACKEND_DIR / "data" / "recipes"


@lru_cache
def get_settings() -> Settings:
    return Settings()
