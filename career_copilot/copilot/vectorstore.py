"""RAG steps 3-4 - Embeddings + vector DB (ChromaDB, local all-MiniLM-L6-v2) + retrieval."""
import hashlib
import sys

try:  # Streamlit Cloud ships an old sqlite3; use the bundled one if available
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

import chromadb  # noqa: E402

from .chunker import chunk_text  # noqa: E402
from .loader import load_file  # noqa: E402


class VectorStore:
    def __init__(self, path: str = "chroma_db", name: str = "career_docs"):
        self.client = chromadb.PersistentClient(path=path)
        self.col = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def add_file(self, filename: str, data: bytes, chunk_size=800, overlap=120) -> int:
        file_id = hashlib.md5(data).hexdigest()[:10]
        if self.col.get(where={"file_id": file_id}, limit=1)["ids"]:
            return 0
        ids, docs, metas = [], [], []
        for page in load_file(filename, data):
            for j, chunk in enumerate(chunk_text(page["text"], chunk_size, overlap)):
                ids.append(f"{file_id}-{page['page'] or 0}-{j}")
                docs.append(chunk)
                metas.append({"source": filename, "page": page["page"] or 0, "idx": j, "file_id": file_id})
        if docs:
            self.col.add(ids=ids, documents=docs, metadatas=metas)
        return len(docs)

    def search(self, query: str, k: int = 4, min_similarity: float = 0.15) -> list[dict]:
        if self.col.count() == 0:
            return []
        res = self.col.query(query_texts=[query], n_results=min(k, self.col.count()))
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            sim = 1 - dist
            if sim >= min_similarity:
                hits.append({"text": doc, "source": meta["source"], "page": meta["page"], "score": sim})
        return hits

    def get_text(self, source: str | None = None) -> str:
        """Full text of one source (or all), in reading order - used for ATS matching."""
        data = self.col.get(where={"source": source}) if source else self.col.get()
        rows = sorted(zip(data["documents"], data["metadatas"]),
                      key=lambda r: (r[1]["source"], r[1]["page"], r[1]["idx"]))
        return "\n".join(d for d, _ in rows)

    def sources(self) -> list[str]:
        return sorted({m["source"] for m in self.col.get()["metadatas"]})

    def count(self) -> int:
        return self.col.count()

    def reset(self):
        name = self.col.name
        self.client.delete_collection(name)
        self.col = self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
