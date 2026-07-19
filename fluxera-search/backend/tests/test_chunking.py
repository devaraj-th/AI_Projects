from app.utils.chunking import chunk_text


def test_chunking_non_empty() -> None:
    text = "A" * 5000
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    assert len(chunks) > 3
    assert all(chunks)


def test_chunking_empty() -> None:
    assert chunk_text("   ") == []
