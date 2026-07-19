def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    if not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end]

        if end < length:
            split_at = max(chunk.rfind("\n\n"), chunk.rfind(". "), chunk.rfind("\n"))
            if split_at > int(chunk_size * 0.4):
                end = start + split_at + 1
                chunk = text[start:end]

        chunks.append(chunk.strip())
        if end >= length:
            break

        next_start = end - overlap
        # Ensure forward progress for short docs where overlap can exceed the current end.
        start = next_start if next_start > start else end

    return [c for c in chunks if c]
