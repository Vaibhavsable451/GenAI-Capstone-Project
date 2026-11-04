"""RAG step 2 - Chunking: recursive split + overlap."""

SEPARATORS = ["\n\n", "\n", ". ", " "]


def _split(text: str, size: int, seps: list[str]) -> list[str]:
    if len(text) <= size:
        return [text]
    if not seps:
        return [text[i:i + size] for i in range(0, len(text), size)]
    sep, rest = seps[0], seps[1:]
    out = []
    for p in text.split(sep):
        out.extend(_split(p, size, rest) if len(p) > size else [p])
    return out


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    pieces = [p.strip() for p in _split(text, chunk_size, SEPARATORS) if p.strip()]
    chunks, current = [], ""
    for p in pieces:
        if current and len(current) + len(p) + 1 > chunk_size:
            chunks.append(current)
            current = (current[-overlap:] + " " + p) if overlap else p
        else:
            current = f"{current} {p}".strip()
    if current:
        chunks.append(current)
    return chunks
