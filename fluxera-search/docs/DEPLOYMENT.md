# Deployment Guide

## Local Docker Compose

1. Copy env file:

   `cp .env.example .env`

2. Start stack:

   `docker compose up --build`

3. Pull models in Ollama container:

   `docker exec -it fluxera-ollama ollama pull qwen3:8b`

   `docker exec -it fluxera-ollama ollama pull bge-m3`

4. Open apps:

   - Frontend: `http://localhost:3000`
   - Backend API docs: `http://localhost:8000/docs`

## Production Notes

- Place backend and frontend behind a reverse proxy.
- Replace static `SECRET_KEY` with managed secrets.
- Configure backups for PostgreSQL volume.
- Scale FastAPI and Next.js using horizontal replicas.
- For high throughput inference, switch to vLLM OpenAI-compatible endpoint.
