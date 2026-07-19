# Fluxera Search API

Base URL: `http://localhost:8000`

## Authentication

### POST /auth/login

Request:

```json
{
  "email": "admin@fluxera.ai",
  "password": "admin123"
}
```

Response:

```json
{
  "access_token": "...",
  "token_type": "bearer"
}
```

## Chat

### POST /chat

Streams Server-Sent Events with token chunks and final citation payload.

Request:

```json
{
  "question": "Explain WAFL Snapshot architecture",
  "conversation_id": null,
  "model": "Fluxera AI",
  "temperature": 0.2,
  "top_p": 0.9,
  "max_tokens": 700
}
```

SSE event types:

- `token`
- `done` (includes `conversation_id`, `citations`, and `follow_ups`)

## Upload

### POST /upload

Multipart file upload for PDF, DOCX, TXT, Markdown, HTML.

## Search

### POST /search

Performs vector search over embedded chunks.

## History

### GET /history

Returns conversation list.

### GET /history/{conversation_id}

Returns messages and citations for a conversation.

## Documents

### GET /documents

Returns uploaded documents and status.

## Admin

### GET /admin/stats

Returns aggregate counts for users, documents, chunks, and conversations.
