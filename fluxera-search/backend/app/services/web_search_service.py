from dataclasses import dataclass
import re

import httpx


@dataclass
class WebSearchResult:
    title: str
    url: str
    snippet: str


class WebSearchService:
    def _normalize_query(self, query: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", query).lower()
        stop_words = {
            "what",
            "who",
            "when",
            "where",
            "why",
            "how",
            "is",
            "are",
            "the",
            "a",
            "an",
            "of",
            "in",
            "to",
            "for",
            "and",
            "today",
        }
        terms = [term for term in cleaned.split() if term and term not in stop_words]
        return " ".join(terms) or query

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        # No API key required: Wikipedia search API supports full-text retrieval.
        normalized_query = self._normalize_query(query)
        params = {
            "action": "query",
            "list": "search",
            "srsearch": normalized_query,
            "srlimit": max_results,
            "utf8": 1,
            "format": "json",
        }
        try:
            headers = {
                "User-Agent": "FluxeraSearchBot/1.0 (https://github.com/devaraj-th/AI_Projects)",
            }
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                response = await client.get("https://en.wikipedia.org/w/api.php", params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

        query_payload = payload.get("query", {}) if isinstance(payload, dict) else {}
        search_rows = query_payload.get("search", []) if isinstance(query_payload, dict) else []
        if not isinstance(search_rows, list):
            return []

        results: list[WebSearchResult] = []
        for row in search_rows:
            title = str(row.get("title", "")).strip()
            page_id = row.get("pageid")
            raw_snippet = str(row.get("snippet", "")).strip()
            snippet = re.sub(r"<[^>]+>", "", raw_snippet) or "No summary available."
            if not title or not page_id:
                continue
            url = f"https://en.wikipedia.org/?curid={page_id}"
            results.append(WebSearchResult(title=title, url=url, snippet=snippet))

        return results
