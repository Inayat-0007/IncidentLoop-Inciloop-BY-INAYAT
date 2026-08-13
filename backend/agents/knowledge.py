from __future__ import annotations

import asyncio
from typing import Any

from backend.rag.retriever import retrieve


async def retrieve_knowledge(query: str) -> dict[str, Any]:
    hits = await asyncio.to_thread(retrieve, query, 4)
    return {
        "docs": hits,
        "ids": [h["id"] for h in hits],
        "tools": ["rag.retrieve"],
    }
