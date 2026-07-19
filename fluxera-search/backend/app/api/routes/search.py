from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.chat import SearchRequest
from app.services.retrieval_service import RetrievalService


router = APIRouter()


@router.post("")
async def search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    service = RetrievalService(db)
    hits = await service.search(payload.query, payload.top_k)
    return {"results": [hit.model_dump() for hit in hits]}
