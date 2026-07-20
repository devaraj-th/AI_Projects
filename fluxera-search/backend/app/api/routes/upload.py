from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
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
    if len(data) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max allowed size is {settings.upload_max_mb} MB.",
        )

    service = IngestService(db)
    try:
        document = await service.ingest_upload(file.filename, data, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {exc}") from exc

    from app.db.models import DocumentChunk
    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
    out = DocumentOut.model_validate(document)
    out.chunk_count = chunk_count
    return out


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
