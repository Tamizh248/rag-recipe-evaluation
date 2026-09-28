from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.chunking.generic_chunker import chunk_text
from app.core.logging import get_logger
from app.embeddings.sentence_transformer import EmbeddingModel
from app.ingestion.loader import SUPPORTED_EXTENSIONS, extract_text
from app.models.document import DocumentInfo, UploadedChunk, UploadedChunkMetadata
from app.vectorstore.chroma_store import ChromaStore

logger = get_logger(__name__)


class DocumentUploadError(Exception):
    """Raised when an uploaded file is rejected before/instead of ingestion."""


def upload_document(
    filename: str,
    content: bytes,
    embedding_model: EmbeddingModel,
    store: ChromaStore,
    chunk_size: int,
    chunk_overlap: int,
    max_file_size_mb: int,
) -> DocumentInfo:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DocumentUploadError(
            f"Unsupported file type {suffix!r}. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_file_size_mb:
        raise DocumentUploadError(
            f"File too large ({size_mb:.1f}MB); the limit is {max_file_size_mb}MB"
        )

    text = extract_text(filename, content)
    if not text.strip():
        raise DocumentUploadError(
            f"No extractable text found in {filename!r} - it may be a scanned/image-only "
            "file. OCR is not supported yet, so this file can't be ingested."
        )

    doc_id = uuid4().hex
    uploaded_at = datetime.now(timezone.utc).isoformat()
    pieces = chunk_text(text, chunk_size, chunk_overlap)
    if not pieces:
        raise DocumentUploadError(f"Chunking produced zero chunks for {filename!r}")

    chunks = [
        UploadedChunk(
            text=piece,
            metadata=UploadedChunkMetadata(
                chunk_id=f"{doc_id}_{index:04d}",
                doc_id=doc_id,
                source_file=filename,
                chunk_index=index,
                uploaded_at=uploaded_at,
            ),
        )
        for index, piece in enumerate(pieces)
    ]

    embeddings = embedding_model.embed_texts([c.text for c in chunks])
    store.add_uploaded_chunks(chunks, embeddings)

    logger.info("Uploaded %s -> doc_id=%s, %d chunks", filename, doc_id, len(chunks))
    return DocumentInfo(doc_id=doc_id, source_file=filename, chunk_count=len(chunks), uploaded_at=uploaded_at)


def list_documents(store: ChromaStore) -> list[DocumentInfo]:
    return store.list_uploaded_documents()


def delete_document(store: ChromaStore, doc_id: str) -> bool:
    existing = store.get_all_uploaded(doc_id)
    if not existing:
        return False
    store.delete_uploaded_document(doc_id)
    return True
