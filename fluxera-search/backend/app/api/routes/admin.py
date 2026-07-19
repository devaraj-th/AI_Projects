from sqlalchemy import func
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Conversation, Document, DocumentChunk, User
from app.db.session import get_db
from app.services.ingest_service import IngestService
from app.services.model_router import MODEL_ROUTING


router = APIRouter()


@router.get("/stats")
def stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    return {
        "documents": db.query(func.count(Document.id)).scalar(),
        "chunks": db.query(func.count(DocumentChunk.id)).scalar(),
        "users": db.query(func.count(User.id)).scalar(),
        "conversations": db.query(func.count(Conversation.id)).scalar(),
        "models": list(MODEL_ROUTING.keys()),
        "embedding_status": {
            "embedded": db.query(func.count(Document.id)).filter(Document.status == "embedded").scalar(),
            "embedding": db.query(func.count(Document.id)).filter(Document.status == "embedding").scalar(),
        },
    }


@router.post("/seed-demo-context")
async def seed_demo_context(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    existing = db.query(Document).filter(Document.source_type == "seed").first()
    if existing:
        return {"seeded": False, "message": "Seed context already exists"}

    service = IngestService(db)
    seeded_docs = [
        (
            "Asynchronous Systems Notes",
            """
Asynchronous systems allow different components to progress independently without waiting for each other.
Message queues and event streams are common patterns used to decouple producers and consumers.
Failures are handled with retries, idempotency keys, dead-letter queues, and circuit breakers.
Eventual consistency is expected, so APIs should communicate state transitions clearly.
""".strip(),
        ),
        (
            "Upload Troubleshooting Guide",
            """
If document upload fails, verify file format support first: pdf, docx, txt, md, html.
If the model backend is unavailable, embeddings may fall back to deterministic vectors in development.
For large files, split content into smaller sections and upload under the configured size limit.
""".strip(),
        ),
    ]

    for title, text in seeded_docs:
        await service.ingest_text(title=title, text=text, source_uri="seed://demo")

    return {"seeded": True, "documents": len(seeded_docs)}
