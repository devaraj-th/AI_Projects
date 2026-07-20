from app.schemas.chat import SearchHit


def rerank_hits(query: str, hits: list[SearchHit]) -> list[SearchHit]:
    normalized_query = query.lower().strip()
    query_terms = [term for term in normalized_query.split() if term.strip()]
    query_set = set(query_terms)

    scored: list[tuple[float, SearchHit]] = []
    for hit in hits:
        content = hit.content.lower()
        content_terms = content.split()
        unique_content_terms = set(content_terms)

        overlap = len(query_set.intersection(unique_content_terms))
        overlap_ratio = overlap / max(len(query_set), 1)
        phrase_bonus = 0.08 if normalized_query and normalized_query in content else 0.0

        # Reward concentrated keyword density, but cap impact to avoid lexical overfitting.
        density = overlap / max(min(len(content_terms), 200), 1)
        density_bonus = min(density * 1.5, 0.06)

        rerank_score = hit.score + (overlap_ratio * 0.15) + phrase_bonus + density_bonus
        scored.append((rerank_score, hit))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [hit for _, hit in scored]
