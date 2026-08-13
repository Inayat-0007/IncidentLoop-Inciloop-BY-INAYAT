from __future__ import annotations

from typing import Any

from backend.rag.retriever import retrieve


def retrieve_knowledge(query: str) -> dict[str, Any]:
    hits = retrieve(query, k=4)
    return {
        "docs": hits,
        "ids": [h["id"] for h in hits],
        "tools": ["rag.retrieve"],
    }
