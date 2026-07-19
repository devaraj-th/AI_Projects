import json
import time
from collections.abc import AsyncGenerator

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Conversation, Message
from app.schemas.chat import Citation, ChatRequest
from app.services.model_router import resolve_model
from app.services.retrieval_service import RetrievalService
from app.services.web_search_service import WebSearchService


SYSTEM_PROMPT = """You are Fluxera Search, a friendly enterprise AI assistant.
Always start your response with a short greeting.
Answer only from the provided context.
If context includes [Wn] web sources, use them directly to answer.
If web sources are provided, do not reply with "I do not know".
When you use local context, include [n] citation markers.
When you use web context, include [Wn] citation markers.
If neither context contains the answer, reply exactly: "Hello! I do not know based on the available context."
Do not use outside knowledge.
"""


class ChatService:
    def __init__(self, db: Session, user_id: int) -> None:
        self.db = db
        self.user_id = user_id

    async def stream_answer(self, req: ChatRequest) -> AsyncGenerator[str, None]:
        retrieval = RetrievalService(self.db)
        try:
            hits = await retrieval.search(req.question, top_k=10)
        except Exception:
            # Keep chat available even if retrieval backend is temporarily unavailable.
            hits = []

        # Guardrail: treat low-similarity matches as out-of-context.
        hits = [hit for hit in hits if hit.score >= settings.retrieval_min_score]

        # Avoid false positives from vector-only similarity by requiring lexical overlap.
        punctuation = ".,!?;:\"'()[]{}"
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

        query_terms = {
            term.strip(punctuation).lower()
            for term in req.question.split()
            if len(term.strip()) > 2 and term.strip(punctuation).lower() not in stop_words
        }

        def has_overlap(content: str) -> bool:
            content_terms = {
                token.strip(punctuation).lower()
                for token in content.split()
                if len(token.strip()) > 2
            }
            return bool(query_terms.intersection(content_terms))

        hits = [hit for hit in hits if has_overlap(hit.content)]

        web_results = []
        use_web = False
        top_local_score = hits[0].score if hits else 0.0
        local_is_weak = (not hits) or (top_local_score < settings.web_fallback_score_threshold)
        if local_is_weak and settings.web_search_enabled:
            web_results = await WebSearchService().search(req.question, max_results=settings.web_search_max_results)
            use_web = bool(web_results)

        if use_web:
            # Prefer explicit web evidence over weak local matches.
            hits = []

        citations: list[Citation] = []
        if hits:
            citations = [
                Citation(
                    id=i + 1,
                    document_id=hit.document_id,
                    title=hit.title,
                    source_uri=None,
                    chunk_index=hit.chunk_index,
                    score=hit.score,
                    excerpt=hit.content[:300],
                )
                for i, hit in enumerate(hits)
            ]
        elif use_web:
            citations = [
                Citation(
                    id=i + 1,
                    document_id=0,
                    title=result.title,
                    source_uri=result.url,
                    chunk_index=i,
                    score=1.0,
                    excerpt=result.snippet[:300],
                )
                for i, result in enumerate(web_results)
            ]

        conversation = self._get_or_create_conversation(req)
        self.db.add(Message(conversation_id=conversation.id, role="user", content=req.question))
        self.db.commit()

        if not hits and not use_web:
            out_of_context = "Hello! I do not know based on the available context."
            self.db.add(
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=out_of_context,
                    citations_json="[]",
                )
            )
            self.db.commit()
            yield f"data: {json.dumps({'type': 'token', 'token': out_of_context})}\n\n"
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "done",
                        "conversation_id": conversation.id,
                        "citations": [],
                        "follow_ups": [],
                    }
                )
                + "\n\n"
            )
            return

        if hits:
            context_lines = [f"[{i + 1}] {hit.title} (chunk {hit.chunk_index}): {hit.content}" for i, hit in enumerate(hits)]
        else:
            context_lines = [f"[W{i + 1}] {result.title}: {result.snippet} ({result.url})" for i, result in enumerate(web_results)]

        prompt = (
            (req.system_prompt or SYSTEM_PROMPT)
            + "\n\nContext:\n"
            + "\n\n".join(context_lines)
            + f"\n\nQuestion: {req.question}"
        )

        started = time.perf_counter()
        answer_text = ""
        try:
            async for token in self._stream_from_model(prompt, req):
                answer_text += token
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
        except Exception as exc:
            error_text = f"Model generation failed: {exc}"
            self.db.add(
                Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=error_text,
                    citations_json="[]",
                )
            )
            self.db.commit()
            yield f"data: {json.dumps({'type': 'error', 'error': error_text})}\n\n"
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "done",
                        "conversation_id": conversation.id,
                        "citations": [],
                        "follow_ups": [],
                    }
                )
                + "\n\n"
            )
            return

        latency_ms = (time.perf_counter() - started) * 1000
        self.db.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=answer_text,
                citations_json=json.dumps([c.model_dump() for c in citations]),
                latency_ms=latency_ms,
            )
        )
        self.db.commit()

        yield (
            "data: "
            + json.dumps(
                {
                    "type": "done",
                    "conversation_id": conversation.id,
                    "citations": [c.model_dump() for c in citations],
                    "follow_ups": [
                        "Explain simply",
                        "Give example",
                        "Show diagram",
                        "Compare alternatives",
                    ],
                }
            )
            + "\n\n"
        )

    async def _stream_from_model(self, prompt: str, req: ChatRequest) -> AsyncGenerator[str, None]:
        model = resolve_model(req.model or settings.default_model)
        provider = settings.llm_provider

        if provider == "ollama":
            async with httpx.AsyncClient(timeout=90) as client:
                async with client.stream(
                    "POST",
                    f"{settings.llm_base_url.rstrip('/')}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": req.temperature,
                            "top_p": req.top_p,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        payload = json.loads(line)
                        token = payload.get("response", "")
                        if token:
                            yield token
            return

        # OpenAI-compatible fallback for vLLM or hosted endpoints.
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        async with httpx.AsyncClient(timeout=90) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "stream": True,
                    "temperature": req.temperature,
                    "top_p": req.top_p,
                    "max_tokens": req.max_tokens,
                    "messages": [
                        {"role": "system", "content": "You are an enterprise search assistant."},
                        {"role": "user", "content": prompt},
                    ],
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    body = line.removeprefix("data:").strip()
                    if body == "[DONE]":
                        break
                    payload = json.loads(body)
                    delta = payload.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token

    def _get_or_create_conversation(self, req: ChatRequest) -> Conversation:
        if req.conversation_id:
            convo = self.db.get(Conversation, req.conversation_id)
            if convo and convo.user_id == self.user_id:
                return convo

        conversation = Conversation(
            user_id=self.user_id,
            title=req.question[:80],
            model=req.model,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
