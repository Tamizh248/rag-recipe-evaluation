from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import get_retriever, get_store, get_uploaded_chat_service
from app.core.config import get_settings
from app.embeddings.sentence_transformer import get_embedding_model
from app.ingestion.loader import SUPPORTED_EXTENSIONS
from app.models.chat import ChatResponse
from app.models.document import (
    DocumentInfo,
    DocumentListResponse,
    SupportedFormatsResponse,
    UploadedChatRequest,
    UploadedSearchRequest,
    UploadedSearchResponse,
    UploadedSearchResultItem,
)
from app.retrieval.retriever import Retriever
from app.services import document_service
from app.services.uploaded_chat_service import UploadedChatService
from app.vectorstore.chroma_store import ChromaStore

router = APIRouter()


@router.get("/api/documents/supported-formats", response_model=SupportedFormatsResponse)
def supported_formats() -> SupportedFormatsResponse:
    return SupportedFormatsResponse(extensions=sorted(SUPPORTED_EXTENSIONS))


@router.post("/api/documents/upload", response_model=DocumentInfo)
async def upload(
    file: UploadFile,
    store: ChromaStore = Depends(get_store),
) -> DocumentInfo:
    settings = get_settings()
    content = await file.read()
    try:
        return document_service.upload_document(
            filename=file.filename or "upload",
            content=content,
            embedding_model=get_embedding_model(),
            store=store,
            chunk_size=settings.upload_chunk_size,
            chunk_overlap=settings.upload_chunk_overlap,
            max_file_size_mb=settings.upload_max_file_size_mb,
        )
    except document_service.DocumentUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/documents", response_model=DocumentListResponse)
def list_documents(store: ChromaStore = Depends(get_store)) -> DocumentListResponse:
    return DocumentListResponse(documents=document_service.list_documents(store))


@router.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, store: ChromaStore = Depends(get_store)) -> dict:
    deleted = document_service.delete_document(store, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Unknown doc_id: {doc_id}")
    return {"deleted": True, "doc_id": doc_id}


@router.post("/api/documents/search", response_model=UploadedSearchResponse)
def search_uploaded(
    request: UploadedSearchRequest, retriever: Retriever = Depends(get_retriever)
) -> UploadedSearchResponse:
    retrieved = retriever.search_uploaded(request.question, top_k=request.top_k, doc_id=request.doc_id)
    results = [
        UploadedSearchResultItem(
            chunk_id=r.chunk_id,
            score=r.score,
            doc_id=r.metadata.doc_id,
            source_file=r.metadata.source_file,
            text=r.text,
            metadata=r.metadata,
        )
        for r in retrieved
    ]
    return UploadedSearchResponse(results=results)


@router.post("/api/documents/chat", response_model=ChatResponse)
def chat_with_documents(
    request: UploadedChatRequest, service: UploadedChatService = Depends(get_uploaded_chat_service)
) -> ChatResponse:
    return service.answer(request.question, doc_id=request.doc_id)
