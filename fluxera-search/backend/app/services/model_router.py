MODEL_ROUTING = {
    "Fluxera AI": "qwen2.5:1.5b",
    "Qwen": "qwen2.5:1.5b",
    "Llama": "llama3.1:8b",
    "DeepSeek": "deepseek-r1:8b",
    "GPT": "gpt-4o-mini",
    "Claude": "claude-3-5-sonnet",
}


def resolve_model(model_label: str) -> str:
    return MODEL_ROUTING.get(model_label, model_label)
