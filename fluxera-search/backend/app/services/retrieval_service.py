from collections import defaultdict

from sqlalchemy import Select, case, desc, or_, select
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
        candidate_limit = max(k * 5, 30)

        dense_stmt: Select[tuple[DocumentChunk, Document, float]] = (
            select(
                DocumentChunk,
                Document,
                (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("score"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .order_by(desc("score"))
            .limit(candidate_limit)
        )

        dense_rows = self.db.execute(dense_stmt).all()
        dense_hits = [
            SearchHit(
                chunk_id=chunk.id,
                document_id=doc.id,
                title=doc.title,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=float(score),
            )
            for chunk, doc, score in dense_rows
        ]

        lexical_hits = self._lexical_search(query, candidate_limit)

        fused_hits = self._fuse_hits_with_rrf(dense_hits, lexical_hits, k)
        return rerank_hits(query, fused_hits)

    def _lexical_search(self, query: str, limit: int) -> list[SearchHit]:
        terms = [term.strip().lower() for term in query.split() if len(term.strip()) > 2]
        if not terms:
            return []

        conditions = [DocumentChunk.content.ilike(f"%{term}%") for term in terms]
        overlap_expr = sum(case((DocumentChunk.content.ilike(f"%{term}%"), 1), else_=0) for term in terms).label("overlap")

        stmt: Select[tuple[DocumentChunk, Document, int]] = (
            select(
                DocumentChunk,
                Document,
                overlap_expr,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(or_(*conditions))
            .order_by(desc("overlap"), DocumentChunk.chunk_index.asc())
            .limit(limit)
        )

        rows = self.db.execute(stmt).all()
        max_overlap = max((int(overlap) for _, _, overlap in rows), default=1)
        return [
            SearchHit(
                chunk_id=chunk.id,
                document_id=doc.id,
                title=doc.title,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=float(overlap) / max_overlap,
            )
            for chunk, doc, overlap in rows
        ]

    def _fuse_hits_with_rrf(self, dense_hits: list[SearchHit], lexical_hits: list[SearchHit], k: int) -> list[SearchHit]:
        rrf_k = 60
        fused_scores: dict[int, float] = defaultdict(float)
        dense_score_by_chunk: dict[int, float] = {}
        lexical_score_by_chunk: dict[int, float] = {}
        hit_by_chunk: dict[int, SearchHit] = {}

        for rank, hit in enumerate(dense_hits, start=1):
            fused_scores[hit.chunk_id] += 1.0 / (rrf_k + rank)
            dense_score_by_chunk[hit.chunk_id] = hit.score
            hit_by_chunk.setdefault(hit.chunk_id, hit)

        for rank, hit in enumerate(lexical_hits, start=1):
            fused_scores[hit.chunk_id] += 1.0 / (rrf_k + rank)
            lexical_score_by_chunk[hit.chunk_id] = hit.score
            if hit.chunk_id not in hit_by_chunk:
                hit_by_chunk[hit.chunk_id] = hit

        ranked = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
        results: list[SearchHit] = []
        for chunk_id, fused_score in ranked[:k]:
            base_hit = hit_by_chunk[chunk_id]
            dense_score = dense_score_by_chunk.get(chunk_id, 0.0)
            lexical_score = lexical_score_by_chunk.get(chunk_id, 0.0)
            relevance = (dense_score * 0.75) + (lexical_score * 0.25)

            # RRF rank signal boosts ties while preserving similarity semantics expected by chat filters.
            boosted_relevance = min(relevance + (fused_score * 0.5), 0.999)
            results.append(
                SearchHit(
                    chunk_id=base_hit.chunk_id,
                    document_id=base_hit.document_id,
                    title=base_hit.title,
                    chunk_index=base_hit.chunk_index,
                    content=base_hit.content,
                    score=float(boosted_relevance),
                )
            )

        return results

