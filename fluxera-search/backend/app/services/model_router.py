from app.core.config import settings


MODEL_ROUTING = {
    "Fluxera AI": "qwen2.5:1.5b",
    "Qwen": "qwen2.5:1.5b",
    "Llama": "llama3.1:8b",
    "DeepSeek": "deepseek-r1:8b",
    "GPT": "gpt-4o-mini",
    "Claude": "claude-3-5-sonnet",
}


def resolve_model(model_label: str) -> str:
    resolved = MODEL_ROUTING.get(model_label, model_label)
    if settings.llm_provider == "ollama" and resolved in {"gpt-4o-mini", "claude-3-5-sonnet"}:
        return settings.default_model
    return resolved
