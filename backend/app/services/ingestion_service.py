from dataclasses import dataclass
from pathlib import Path

from app.chunking.base import Chunker, RecipeDocument
from app.core.logging import get_logger
from app.embeddings.sentence_transformer import EmbeddingModel
from app.ingestion.loader import load_documents
from app.ingestion.metadata import IngestionError, validate_parsed_recipe
from app.ingestion.parser import parse_recipe, strip_frontmatter
from app.models.chunk import Chunk
from app.vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)

# The evaluation dataset is exactly these 6 new recipe cards. Ingestion is
# pinned to this explicit list (rather than "everything in the directory")
# so the pipeline can never accidentally re-index an old/larger corpus.
RECIPE_FILES = [
    "sourdough_country_2kg.txt",
    "rye_sourdough_900g.txt",
    "rosemary_olive_focaccia_1500g.txt",
    "brioche_sourdough_900g.txt",
    "cinnamon_raisin_walnut_800g.txt",
    "whole_wheat_flaxseed_1800g.txt",
]


@dataclass
class IngestionResult:
    strategy: str
    recipe_count: int
    chunk_count: int
    chunk_ids: list[str]


def ingest_recipes(
    recipes_dir: Path,
    chunker: Chunker,
    embedding_model: EmbeddingModel,
    store: ChromaStore,
    reset: bool = True,
) -> IngestionResult:
    documents = load_documents(recipes_dir, filenames=RECIPE_FILES)
    if len(documents) != len(RECIPE_FILES):
        raise IngestionError(
            f"Expected exactly {len(RECIPE_FILES)} recipe cards, found {len(documents)}"
        )

    all_chunks: list[Chunk] = []
    for doc in documents:
        parsed = parse_recipe(doc.source_file, doc.text)
        validate_parsed_recipe(parsed)
        body = strip_frontmatter(doc.text)
        document = RecipeDocument(parsed=parsed, body=body)
        chunks = chunker.chunk(document)
        if not chunks:
            raise IngestionError(f"Ingestion failure: chunker produced zero chunks for {doc.source_file}")
        all_chunks.extend(chunks)
        logger.info("Chunked %s -> %d chunks (%s)", doc.source_file, len(chunks), chunker.strategy)

    if reset:
        store.reset_collection(chunker.strategy)

    texts = [c.text for c in all_chunks]
    embeddings = embedding_model.embed_texts(texts)
    store.add_chunks(chunker.strategy, all_chunks, embeddings)

    logger.info(
        "Ingested %d recipes -> %d chunks into collection for strategy=%s",
        len(documents),
        len(all_chunks),
        chunker.strategy,
    )

    return IngestionResult(
        strategy=chunker.strategy,
        recipe_count=len(documents),
        chunk_count=len(all_chunks),
        chunk_ids=[c.chunk_id for c in all_chunks],
    )
