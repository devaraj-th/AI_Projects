from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Document, User
from app.db.session import get_db
from app.schemas.document import DocumentOut


router = APIRouter()


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[DocumentOut]:
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [DocumentOut.model_validate(doc) for doc in docs]
