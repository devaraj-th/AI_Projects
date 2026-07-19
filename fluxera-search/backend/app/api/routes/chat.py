from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService


router = APIRouter()


@router.post("")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    service = ChatService(db, user_id=user.id)
    return StreamingResponse(service.stream_answer(payload), media_type="text/event-stream")
