from pydantic import BaseModel, Field


class UploadedChunkMetadata(BaseModel):
    chunk_id: str
    doc_id: str
    source_file: str
    chunk_index: int
    uploaded_at: str


class UploadedChunk(BaseModel):
    text: str
    metadata: UploadedChunkMetadata

    @property
    def chunk_id(self) -> str:
        return self.metadata.chunk_id


class DocumentInfo(BaseModel):
    doc_id: str
    source_file: str
    chunk_count: int
    uploaded_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class UploadedSearchRequest(BaseModel):
    question: str
    top_k: int = 5
    doc_id: str | None = None


class UploadedSearchResultItem(BaseModel):
    chunk_id: str
    score: float
    doc_id: str
    source_file: str
    text: str
    metadata: UploadedChunkMetadata


class UploadedSearchResponse(BaseModel):
    results: list[UploadedSearchResultItem]


class UploadedChatRequest(BaseModel):
    question: str
    doc_id: str | None = None


class SupportedFormatsResponse(BaseModel):
    extensions: list[str] = Field(default_factory=list)
