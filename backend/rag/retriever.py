from __future__ import annotations

from pathlib import Path

from backend.rag.ingest import get_collection, ingest


def retrieve(query: str, k: int = 4) -> list[dict[str, str]]:
    """Query the same Chroma collection ingest writes. Never skip Chroma for keyword rank."""
    col = get_collection()
    if col.count() == 0:
        ingest()
        col = get_collection()
    if col.count() == 0:
        raise RuntimeError("Chroma collection is empty after ingest; RAG cannot skip Chroma")
    n = min(max(k, 1), col.count())
    try:
        result = col.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas"],
        )
    except Exception:
        ingest()
        col = get_collection()
        if col.count() == 0:
            raise RuntimeError("Chroma collection is empty after ingest; RAG cannot skip Chroma")
        n = min(max(k, 1), col.count())
        result = col.query(
            query_texts=[query],
            n_results=n,
            include=["documents", "metadatas"],
        )
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    hits: list[dict[str, str]] = []
    for i, doc_id in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
        title = str(meta.get("title") or Path(str(doc_id)).stem)
        text = documents[i] if i < len(documents) else ""
        hits.append({"id": str(doc_id), "title": title, "text": str(text)})
    return hits
