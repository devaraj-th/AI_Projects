import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, chat, documents, embed, history, search, upload
from app.core.config import settings
from app.db.session import init_db


app = FastAPI(
    title="Fluxera Search API",
    version="0.1.0",
    description="AI-powered enterprise search with RAG and citations.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost(:\d+)?|127\.0\.0\.1(:\d+)?|[a-zA-Z0-9-]+-3000\.app\.github\.dev)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(embed.router, prefix="/embed", tags=["embed"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
