def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    if not text.strip():
        return []

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    min_split = int(chunk_size * 0.5)

    while start < length:
        end = min(start + chunk_size, length)

        if end < length:
            window = normalized[start:end]
            split_at = _choose_split_point(window, min_split)
            if split_at is not None:
                end = start + split_at

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= length:
            break

        next_start = max(end - overlap, start + 1)
        start = next_start

    return chunks


def _choose_split_point(window: str, min_split: int) -> int | None:
    delimiters = [
        "\n## ",
        "\n### ",
        "\n\n",
        ". ",
        "? ",
        "! ",
        "\n",
        "; ",
        ", ",
        " ",
    ]

    best = -1
    for delimiter in delimiters:
        idx = window.rfind(delimiter)
        if idx > best and idx >= min_split:
            best = idx + len(delimiter)

    if best <= 0:
        return None

    return best
