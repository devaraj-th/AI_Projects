import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import User
from app.db.session import get_db, SessionLocal
from app.schemas.document import DocumentOut, GitUploadRequest, UrlUploadRequest
from app.services.ingest_service import IngestService  # used by url/git routes


router = APIRouter()


async def _run_ingest_background(document_id: int, filename: str, data: bytes, mime_type: str | None) -> None:
    """Background task: embed chunks into the existing placeholder document.
    Uses its own DB session so it runs after the HTTP response is sent.
    """
    import json
    from app.db.models import Document, DocumentChunk
    from app.services.embedding_service import EmbeddingService
    from app.services.file_parsers import parse_file_bytes
    from app.utils.chunking import chunk_text

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if not document:
            return

        try:
            text = parse_file_bytes(filename, data)
            chunks = chunk_text(text)
        except Exception as exc:
            document.status = "error"
            db.commit()
            return

        if not chunks:
            document.status = "error"
            db.commit()
            return

        if len(chunks) > settings.max_chunks_per_document:
            chunks = chunks[: settings.max_chunks_per_document]

        embedding_service = EmbeddingService()
        embedded_count = 0
        for index, chunk in enumerate(chunks):
            try:
                emb = await embedding_service.embed(chunk)
            except Exception:
                continue
            db.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=index,
                    content=chunk,
                    embedding=emb,
                    metadata_json=json.dumps({
                        "chunk_index": index,
                        "chunk_length": len(chunk),
                        "source_type": "upload",
                        "title": filename,
                    }),
                )
            )
            embedded_count += 1

        document.status = "embedded" if embedded_count > 0 else "error"
        db.commit()
    except Exception:
        try:
            document = db.get(Document, document_id)
            if document:
                document.status = "error"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("", response_model=DocumentOut)
async def upload_document(
    background_tasks: BackgroundTasks,
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

    # Validate file type and create a placeholder document record synchronously
    # so we can return a document ID immediately without blocking on embedding.
    from app.services.file_parsers import parse_file_bytes, SUPPORTED_EXTENSIONS
    from pathlib import Path
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Remove previous uploads with the same filename (dedup).
    from app.db.models import Document
    for old in db.query(Document).filter(Document.title == file.filename, Document.source_type == "upload").all():
        db.delete(old)
    db.flush()

    document = Document(
        title=file.filename,
        source_type="upload",
        source_uri=f"upload://{file.filename}",
        mime_type=file.content_type,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Kick off embedding in a background task — response returns immediately.
    background_tasks.add_task(_run_ingest_background, document.id, file.filename, data, file.content_type)

    out = DocumentOut.model_validate(document)
    out.chunk_count = 0
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
