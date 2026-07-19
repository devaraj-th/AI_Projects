from sqlalchemy import func
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Conversation, Document, DocumentChunk, User
from app.db.session import get_db
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
