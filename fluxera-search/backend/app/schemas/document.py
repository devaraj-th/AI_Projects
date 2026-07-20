from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    title: str
    source_type: str
    source_uri: str | None
    status: str
    chunk_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class UrlUploadRequest(BaseModel):
    url: str


class GitUploadRequest(BaseModel):
    repo_url: str
    branch: str = "main"

