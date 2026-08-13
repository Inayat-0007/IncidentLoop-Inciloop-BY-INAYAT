from __future__ import annotations

import hashlib
import re
from pathlib import Path

from backend.config import CHROMA_PATH, DATA_DIR, KNOWLEDGE_DIR

COLLECTION_NAME = "devopspilot"
_TOKEN = re.compile(r"[a-z0-9]+")


class HashEmbeddingFunction:
    """Offline token-hash embeddings so Docker/CI never download sentence-transformers.

    Same function is used for ingest upserts and Chroma query_texts (no keyword bypass).
    """

    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    def name(self) -> str:
        return "devopspilot-hash-v2"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        return self(input)

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        tokens = _TOKEN.findall((text or "").lower().replace("-", " ").replace("/", " "))
        grams = list(tokens)
        grams.extend(f"{a}_{b}" for a, b in zip(tokens, tokens[1:]))
        for tok in grams:
            digest = hashlib.sha256(tok.encode("utf-8", errors="replace")).digest()
            idx = int.from_bytes(digest[:4], "little") % self._dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


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


def chroma_client():
    import chromadb

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_collection(client=None, *, reset: bool = False):
    """Open the DevOpsPilot collection with the ingest embedding function."""
    c = client or chroma_client()
    ef = HashEmbeddingFunction()
    if reset:
        try:
            c.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    try:
        return c.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)
    except Exception:
        try:
            c.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        return c.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def ingest(root: Path | None = None) -> int:
    """Load knowledge/ into Chroma. Markdown is the source format (see docs/STACK.md)."""
    docs = load_markdown_docs(root)
    col = get_collection(reset=True)
    if docs:
        col.upsert(
            ids=[d["id"] for d in docs],
            documents=[f"{d['id']}\n{d['title']}\n{d['text']}" for d in docs],
            metadatas=[{"title": d["title"]} for d in docs],
        )
    return len(docs)
