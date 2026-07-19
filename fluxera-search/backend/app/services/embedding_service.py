import hashlib

import httpx

from app.core.config import settings


class EmbeddingService:
    def __init__(self) -> None:
        self.base_url = settings.embedding_base_url.rstrip("/")

    async def embed(self, text: str) -> list[float]:
        if settings.embedding_provider == "ollama":
            return await self._embed_ollama(text)
        if settings.embedding_provider in {"openai", "openai-compatible", "vllm"}:
            return await self._embed_openai_compatible(text)
        return self._fallback_embedding(text)

    async def _embed_ollama(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            # Ollama >=0.3 uses /api/embed with "input". Older versions use /api/embeddings with "prompt".
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": settings.embedding_model, "input": text},
            )
            if response.status_code == 404:
                legacy_response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": settings.embedding_model, "prompt": text},
                )
                legacy_response.raise_for_status()
                legacy_payload = legacy_response.json()
                return legacy_payload.get("embedding") or self._fallback_embedding(text)

            response.raise_for_status()
            payload = response.json()
            embedding = payload.get("embedding")
            if embedding:
                return embedding

            embeddings = payload.get("embeddings")
            if embeddings and isinstance(embeddings, list) and embeddings[0]:
                return embeddings[0]

            return self._fallback_embedding(text)

    async def _embed_openai_compatible(self, text: str) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/v1/embeddings",
                headers=headers,
                json={"model": settings.embedding_model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", [])
            if data:
                return data[0]["embedding"]
        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str) -> list[float]:
        # Stable deterministic vector for local development when model APIs are unavailable.
        dim = settings.vector_dimension
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = [(digest[i % len(digest)] / 255.0) * 2 - 1 for i in range(dim)]
        return values
