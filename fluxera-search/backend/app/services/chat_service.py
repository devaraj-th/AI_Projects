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


SYSTEM_PROMPT = """You are Fluxera Search, an enterprise AI search assistant.
Answer based only on provided context chunks.
Every paragraph must include [n] style citation markers.
If the answer cannot be found, clearly say you do not know.
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

        conversation = self._get_or_create_conversation(req)
        self.db.add(Message(conversation_id=conversation.id, role="user", content=req.question))
        self.db.commit()

        context_lines = [f"[{i + 1}] {hit.title} (chunk {hit.chunk_index}): {hit.content}" for i, hit in enumerate(hits)]
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
