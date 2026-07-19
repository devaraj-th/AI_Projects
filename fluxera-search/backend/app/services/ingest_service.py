import tempfile
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentChunk
from app.services.embedding_service import EmbeddingService
from app.services.file_parsers import parse_file_bytes
from app.utils.chunking import chunk_text


class IngestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_service = EmbeddingService()

    async def ingest_upload(self, filename: str, payload: bytes, mime_type: str | None = None) -> Document:
        text = parse_file_bytes(filename, payload)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No extractable text found in the uploaded file")
        if len(chunks) > settings.max_chunks_per_document:
            chunks = chunks[: settings.max_chunks_per_document]

        document = Document(
            title=filename,
            source_type="upload",
            source_uri=f"upload://{filename}",
            mime_type=mime_type,
            status="embedding",
        )
        self.db.add(document)
        self.db.flush()

        for index, chunk in enumerate(chunks):
            emb = await self.embedding_service.embed(chunk)
            self.db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    embedding=emb,
                    metadata_json="{}",
                )
            )

        document.status = "embedded"
        self.db.commit()
        self.db.refresh(document)
        return document

    async def ingest_url(self, url: str) -> Document:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "text/html")
        text = parse_file_bytes("page.html", response.content)
        return await self._persist_document(title=url, source_type="web", source_uri=url, text=text, mime_type=content_type)

    async def ingest_git_repo(self, repo_url: str, branch: str = "main") -> Document:
        with tempfile.TemporaryDirectory(prefix="fluxera_repo_") as tmp_dir:
            import subprocess

            subprocess.run(["git", "clone", "--depth", "1", "-b", branch, repo_url, tmp_dir], check=False)

            collected: list[str] = []
            for path in Path(tmp_dir).rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix.lower() not in {".md", ".txt", ".rst", ".py", ".js", ".ts"}:
                    continue
                try:
                    collected.append(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue

            merged = "\n\n".join(collected[:200])
            return await self._persist_document(
                title=repo_url,
                source_type="git",
                source_uri=repo_url,
                text=merged,
                mime_type="text/plain",
            )

    async def ingest_text(self, title: str, text: str, source_uri: str = "seed://local") -> Document:
        return await self._persist_document(
            title=title,
            source_type="seed",
            source_uri=source_uri,
            text=text,
            mime_type="text/plain",
        )

    async def _persist_document(
        self,
        title: str,
        source_type: str,
        source_uri: str,
        text: str,
        mime_type: str | None,
    ) -> Document:
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No extractable text found in the provided source")
        if len(chunks) > settings.max_chunks_per_document:
            chunks = chunks[: settings.max_chunks_per_document]
        document = Document(
            title=title,
            source_type=source_type,
            source_uri=source_uri,
            mime_type=mime_type,
            status="embedding",
        )
        self.db.add(document)
        self.db.flush()

        for index, chunk in enumerate(chunks):
            emb = await self.embedding_service.embed(chunk)
            self.db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    embedding=emb,
                    metadata_json="{}",
                )
            )

        document.status = "embedded"
        self.db.commit()
        self.db.refresh(document)
        return document

