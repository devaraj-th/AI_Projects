from sqlalchemy import Select, desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentChunk
from app.schemas.chat import SearchHit
from app.services.embedding_service import EmbeddingService
from app.services.reranker import rerank_hits


class RetrievalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.embedding_service = EmbeddingService()

    async def search(self, query: str, top_k: int | None = None) -> list[SearchHit]:
        k = top_k or settings.top_k
        embedding = await self.embedding_service.embed(query)

        stmt: Select[tuple[DocumentChunk, Document, float]] = (
            select(
                DocumentChunk,
                Document,
                (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("score"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .order_by(desc("score"))
            .limit(k)
        )

        rows = self.db.execute(stmt).all()
        initial_hits = [
            SearchHit(
                chunk_id=chunk.id,
                document_id=doc.id,
                title=doc.title,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=float(score),
            )
            for chunk, doc, score in rows
        ]
        return rerank_hits(query, initial_hits)

