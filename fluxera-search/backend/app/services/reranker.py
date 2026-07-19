from app.schemas.chat import SearchHit


def rerank_hits(query: str, hits: list[SearchHit]) -> list[SearchHit]:
    query_terms = {term.lower() for term in query.split() if term.strip()}

    scored: list[tuple[float, SearchHit]] = []
    for hit in hits:
        content_terms = set(hit.content.lower().split())
        overlap = len(query_terms.intersection(content_terms))
        rerank_score = hit.score + (overlap * 0.02)
        scored.append((rerank_score, hit))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [hit for _, hit in scored]
