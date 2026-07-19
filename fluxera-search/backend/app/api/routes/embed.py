from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Document, User
from app.db.session import get_db


router = APIRouter()


@router.post("/{document_id}")
def trigger_embed(document_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    doc = db.get(Document, document_id)
    if not doc:
        return {"ok": False, "message": "Document not found"}
    return {"ok": True, "message": "Document already embedded in MVP flow"}
