from pydantic import BaseModel, Field


class Citation(BaseModel):
    id: int
    document_id: int
    title: str
    source_uri: str | None = None
    chunk_index: int
    score: float
    excerpt: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=5000)
    conversation_id: int | None = None
    model: str = "Fluxera AI"
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 700
    system_prompt: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class SearchHit(BaseModel):
    chunk_id: int
    document_id: int
    title: str
    chunk_index: int
    content: str
    score: float
