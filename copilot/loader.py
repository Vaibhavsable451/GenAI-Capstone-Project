"""RAG step 1 - Document processing: PDF / DOCX / TXT / MD -> [{"text", "page"}]."""
import io

from docx import Document
from pypdf import PdfReader


def load_file(name: str, data: bytes) -> list[dict]:
    ext = name.lower().rsplit(".", 1)[-1]
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(data))
        return [{"text": p.extract_text() or "", "page": i + 1} for i, p in enumerate(reader.pages)]
    if ext == "docx":
        doc = Document(io.BytesIO(data))
        return [{"text": "\n".join(p.text for p in doc.paragraphs), "page": None}]
    if ext in ("txt", "md"):
        return [{"text": data.decode("utf-8", errors="ignore"), "page": None}]
    raise ValueError(f"Unsupported file type: .{ext}")
