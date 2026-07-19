from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.document import DocumentOut, GitUploadRequest, UrlUploadRequest
from app.services.ingest_service import IngestService


router = APIRouter()


@router.post("", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentOut:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    service = IngestService(db)
    try:
        document = await service.ingest_upload(file.filename, data, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {exc}") from exc
    return DocumentOut.model_validate(document)


@router.post("/url", response_model=DocumentOut)
async def upload_url(
    payload: UrlUploadRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentOut:
    service = IngestService(db)
    document = await service.ingest_url(payload.url)
    return DocumentOut.model_validate(document)


@router.post("/git", response_model=DocumentOut)
async def upload_git(
    payload: GitUploadRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DocumentOut:
    service = IngestService(db)
    document = await service.ingest_git_repo(payload.repo_url, payload.branch)
    return DocumentOut.model_validate(document)
