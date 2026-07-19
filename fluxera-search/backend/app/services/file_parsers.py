from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}


def parse_file_bytes(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported extension: {suffix}")

    if suffix == ".txt" or suffix == ".md":
        return data.decode("utf-8", errors="ignore")

    if suffix == ".pdf":
        from io import BytesIO

        try:
            reader = PdfReader(BytesIO(data))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(pages)
        except Exception as exc:
            raise ValueError("Unable to parse PDF. The file may be encrypted, corrupted, or image-only.") from exc

    if suffix == ".docx":
        from io import BytesIO

        doc = DocxDocument(BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs])

    soup = BeautifulSoup(data.decode("utf-8", errors="ignore"), "html.parser")
    return soup.get_text("\n")
