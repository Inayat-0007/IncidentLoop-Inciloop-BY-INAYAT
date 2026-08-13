from __future__ import annotations

import asyncio
from typing import Any

from backend.config import heuristic_enabled
from backend.llm import acomplete
from backend.memory import store as memory
from backend.rag.retriever import retrieve


async def retrieve_knowledge(query: str, service: str = "") -> dict[str, Any]:
    hits = await asyncio.to_thread(retrieve, query, 4)
    prior = await asyncio.to_thread(memory.similar_incidents, service or "checkout-api", query, 5)
    citations = [f"{h['id']} ({h.get('title')})" for h in hits]
    rag_blob = "\n".join(f"- {h['id']} [{h.get('title')}]: {(h.get('text') or '')[:500]}" for h in hits)
    mem_blob = "\n".join(
        f"- memory {p.get('id')} service={p.get('service')} rec={p.get('recommendation')} "
        f"resolved={p.get('resolved')} prompt={p.get('prompt')}"
        for p in prior
    )
    user = f"RAG documents:\n{rag_blob or '(none)'}\nPrior incidents from SQLite memory:\n{mem_blob or '(none)'}"
    if heuristic_enabled():
        note = "Retrieved: " + ", ".join(citations)
        if prior:
            note += " | memory: " + ", ".join(str(p.get("id")) for p in prior[:3])
    else:
        note = await acomplete(
            "You are the Knowledge Agent. Summarize retrieved runbooks and past incidents. "
            "Cite document ids and titles. Mention SQLite memory hits if present. "
            "Do not recommend ROLLBACK. Do not invent documents.",
            user,
        )
    return {
        "docs": hits,
        "ids": [h["id"] for h in hits],
        "titles": [h.get("title") or "" for h in hits],
        "memory_hits": prior,
        "summary": note,
        "tools": ["rag.retrieve"],
    }
