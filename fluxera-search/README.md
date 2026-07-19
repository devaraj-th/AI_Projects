# Fluxera Search

Fluxera Search is an enterprise AI search MVP inspired by Perplexity and built for internal knowledge retrieval with mandatory citations.

## Features

- AI search over internal documents
- RAG pipeline with top-k vector retrieval
- Streaming responses with paragraph-level citations
- Follow-up suggestions: explain simply, examples, diagrams, alternatives
- Conversation history and resumable chats
- Document ingestion for PDF, DOCX, TXT, Markdown, HTML
- Admin dashboard with model/user/storage visibility
- Multi-model routing: Fluxera AI, Qwen, Llama, DeepSeek, GPT, Claude

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn-style UI
- Backend: FastAPI, Python, SQLAlchemy
- DB: PostgreSQL + pgvector
- Models: Ollama and OpenAI-compatible APIs (vLLM supported)
- Embeddings: BAAI BGE-M3
- Auth: JWT
- Deployment: Docker Compose

## Architecture

```text
Frontend (Next.js)
  -> FastAPI
    -> Retriever
      -> PostgreSQL + pgvector
        -> LLM (Ollama / vLLM / OpenAI-compatible)
          -> Streaming response + citations
```

## API Surface

- `POST /chat`
- `POST /upload`
- `GET /history`
- `GET /documents`
- `POST /embed/{document_id}`
- `POST /search`

See full details in `docs/API.md`.

## Quick Start

1. Copy config:

   ```bash
   cp .env.example .env
   ```

2. Start services:

   ```bash
   docker compose up --build
   ```

3. Pull required Ollama models:

   ```bash
   docker exec -it fluxera-ollama ollama pull qwen2.5:1.5b
   docker exec -it fluxera-ollama ollama pull bge-m3
   ```

4. Open:

   - App: `http://localhost:3000`
   - API docs: `http://localhost:8000/docs`

## Development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Testing

```bash
cd backend
pytest
```

## Repository Layout

```text
fluxera-search/
  backend/
  frontend/
  infra/postgres/
  docs/
  sample-data/
```

## Production Hardening Checklist

- Add structured logging and tracing (OpenTelemetry)
- Add migration workflow (Alembic)
- Add background workers for async embedding
- Add role-based access control and audit events
- Add observability dashboards and alerting
