from __future__ import annotations

import hashlib
from pathlib import Path

from backend.config import CHROMA_PATH, DATA_DIR, KNOWLEDGE_DIR


class HashEmbeddingFunction:
    """Offline embeddings so Docker/CI never download sentence-transformers."""

    def __init__(self, dim: int = 32) -> None:
        self._dim = dim

    def name(self) -> str:
        return "devopspilot-hash-v1"

    def __call__(self, input: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in input:
            digest = hashlib.sha256(text.encode("utf-8", errors="replace")).digest()
            vec = [((digest[i % len(digest)] - 128) / 128.0) for i in range(self._dim)]
            out.append(vec)
        return out


def load_markdown_docs(root: Path | None = None) -> list[dict[str, str]]:
    base = root or KNOWLEDGE_DIR
    docs: list[dict[str, str]] = []
    if not base.exists():
        return docs
    for path in sorted(base.rglob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        docs.append(
            {
                "id": path.relative_to(base).as_posix(),
                "title": path.stem,
                "text": text,
            }
        )
    return docs


def ingest(root: Path | None = None) -> int:
    """Load knowledge/ into Chroma. Markdown is the source format (see docs/STACK.md)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    docs = load_markdown_docs(root)
    try:
        import chromadb
    except Exception:
        return len(docs)

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = client.get_or_create_collection(
            name="devopspilot",
            embedding_function=HashEmbeddingFunction(),
        )
        if docs:
            col.upsert(
                ids=[d["id"] for d in docs],
                documents=[d["text"] for d in docs],
                metadatas=[{"title": d["title"]} for d in docs],
            )
    except Exception:
        return len(docs)
    return len(docs)
