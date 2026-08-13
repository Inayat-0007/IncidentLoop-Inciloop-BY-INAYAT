from __future__ import annotations

from backend.rag.ingest import load_markdown_docs


def _score(query: str, text: str) -> int:
    q = {t for t in query.lower().replace("/", " ").replace("-", " ").split() if len(t) > 2}
    body = text.lower()
    return sum(1 for t in q if t in body)


def retrieve(query: str, k: int = 4) -> list[dict[str, str]]:
    docs = load_markdown_docs()
    ranked = sorted(docs, key=lambda d: _score(query, d["text"] + " " + d["id"]), reverse=True)
    hits = [d for d in ranked if _score(query, d["text"] + " " + d["id"]) > 0][:k]
    if not hits:
        return ranked[:k]
    return hits
