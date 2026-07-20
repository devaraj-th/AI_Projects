from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Document, DocumentChunk, User
from app.db.session import get_db
from app.schemas.document import DocumentOut


router = APIRouter()


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[DocumentOut]:
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    result = []
    for doc in docs:
        out = DocumentOut.model_validate(doc)
        out.chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        result.append(out)
    return result


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> DocumentOut:
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    out = DocumentOut.model_validate(doc)
    out.chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return out
