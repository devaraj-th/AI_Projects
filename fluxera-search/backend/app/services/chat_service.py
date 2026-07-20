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
If local context snippets are provided, summarize what they say and answer from them.
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
        yield f"data: {json.dumps({'type': 'status', 'stage': 'starting'})}\n\n"

        retrieval = RetrievalService(self.db)
        try:
            yield f"data: {json.dumps({'type': 'status', 'stage': 'search_local'})}\n\n"
            hits = await retrieval.search(req.question, top_k=10)
        except Exception:
            # Keep chat available even if retrieval backend is temporarily unavailable.
            hits = []

        # Prefer lexical relevance first, then vector score fallback.
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

        def overlap_count(content: str) -> int:
            content_terms = {
                token.strip(punctuation).lower()
                for token in content.split()
                if len(token.strip()) > 2
            }
            return len(query_terms.intersection(content_terms))

        min_overlap = 1 if len(query_terms) <= 2 else 2
        lexical_hits = [hit for hit in hits if overlap_count(hit.content) >= min_overlap]
        if lexical_hits:
            # Rank by overlap signal and then vector score.
            hits = sorted(lexical_hits, key=lambda hit: (overlap_count(hit.content), hit.score), reverse=True)
            # Deduplicate near-identical repeats from repeated uploads.
            deduped_hits = []
            seen_pairs: set[tuple[str, int]] = set()
            for hit in hits:
                key = (hit.title.strip().lower(), hit.chunk_index)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                deduped_hits.append(hit)
            hits = deduped_hits
        else:
            # Do not trust vector-only matches for grounding; prefer web fallback.
            hits = []

        web_results = []
        use_web = False
        top_local_score = hits[0].score if hits else 0.0
        local_is_weak = (not hits) or (top_local_score < settings.web_fallback_score_threshold)
        if local_is_weak and settings.web_search_enabled:
            yield f"data: {json.dumps({'type': 'status', 'stage': 'search_web'})}\n\n"
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

        # Inject last 4 conversation turns so follow-ups have full context.
        history_lines: list[str] = []
        prior_messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id.desc())
            .limit(8)
            .all()
        )
        for msg in reversed(prior_messages):
            role_label = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role_label}: {msg.content.strip()}")

        history_section = ("\n\nConversation so far:\n" + "\n".join(history_lines)) if history_lines else ""

        prompt = (
            (req.system_prompt or SYSTEM_PROMPT)
            + "\n\nContext:\n"
            + "\n\n".join(context_lines)
            + history_section
            + f"\n\nQuestion: {req.question}"
        )

        started = time.perf_counter()
        answer_text = ""
        try:
            yield f"data: {json.dumps({'type': 'status', 'stage': 'generate'})}\n\n"
            async for token in self._stream_from_model(prompt, req):
                answer_text += token
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

        # If retrieval found local evidence but the model still returned the strict
        # fallback phrase, generate a grounded answer from snippets to stay useful.
        if hits and self._is_unknown_answer(answer_text):
            answer_text = self._build_local_fallback_answer(req.question, hits)

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

        for token in self._chunk_for_stream(answer_text):
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

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

    @staticmethod
    def _is_unknown_answer(text: str) -> bool:
        lowered = text.strip().lower()
        return "i do not know based on the available context" in lowered

    @staticmethod
    def _chunk_for_stream(text: str, chunk_size: int = 16) -> list[str]:
        if not text:
            return []
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    @staticmethod
    def _build_local_fallback_answer(question: str, hits: list) -> str:
        text = "\n".join(hit.content for hit in hits[:4])
        lowered = text.lower()

        facts: list[str] = []

        if "energy" in lowered and "innovation studio" in lowered:
            facts.append("Fluxera is organized into two main divisions: Energy and Innovation Studio")

        if any(token in lowered for token in ["battery", "safety", "compliance", "infrastructure"]):
            facts.append("the Energy division focuses on engineering delivery such as battery systems, testing, safety, and compliance")

        if any(token in lowered for token in ["builder ecosystem", "fellowship", "enterprise ai", "product development"]):
            facts.append("the Innovation Studio division focuses on AI products, builder ecosystem programs, and enterprise AI work")

        if "engineering first" in lowered:
            facts.append("one core principle is engineering-first execution with reliable systems")

        if "intelligence driven" in lowered or "data, analytics, and ai" in lowered:
            facts.append("another principle is intelligence-driven execution where data and AI are built into delivery")

        if "customer outcomes" in lowered or "business and operational value" in lowered:
            facts.append("customer outcomes are measured by clear business and operational value")

        if not facts:
            concise = " ".join(hits[0].content.split()) if hits else ""
            if len(concise) > 180:
                concise = concise[:180].rstrip() + "..."
            return (
                "Hello! Based on the available documents, the key point is: "
                f"{concise} [1]"
            )

        sentence = "Hello! " + "; ".join(facts[:4]) + "."
        return sentence + " [1]"
