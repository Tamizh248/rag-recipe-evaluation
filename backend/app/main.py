from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, health, ingest, search
from app.core.config import get_settings
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title="Recipe RAG Evaluation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(ingest.router)
app.include_router(documents.router)
