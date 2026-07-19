from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://fluxera:fluxera@postgres:5432/fluxera"
    vector_dimension: int = 1024

    embedding_model: str = "mxbai-embed-large"
    embedding_provider: str = "ollama"
    embedding_base_url: str = "http://ollama:11434"

    llm_provider: str = "ollama"
    llm_base_url: str = "http://ollama:11434"
    llm_api_key: str = ""
    default_model: str = "qwen2.5:1.5b"
    default_temperature: float = 0.2
    default_top_p: float = 0.9
    default_max_tokens: int = 700

    upload_max_mb: int = 50
    top_k: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
