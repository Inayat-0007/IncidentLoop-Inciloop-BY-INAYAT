from __future__ import annotations

from backend.rag.ingest import ingest, load_markdown_docs
from backend.rag.retriever import retrieve


def test_knowledge_corpus_present():
    docs = {d["id"] for d in load_markdown_docs()}
    assert any("database-timeout-runbook" in i for i in docs)
    assert any("checkout-500-runbook" in i for i in docs)
    assert any("deployment-rollback-policy" in i for i in docs)
    assert any("incident-2026-07-18" in i for i in docs)
    assert any("incident-2026-08-02" in i for i in docs)


def test_ingest_and_retrieve_policy():
    n = ingest()
    assert n >= 5
    hits = retrieve("rollback if checkout 500 after deploy and db failures")
    blob = " ".join(h["text"].lower() for h in hits)
    assert "rollback" in blob
    assert "checkout" in blob


def test_chroma_retrieve_checkout_rollback_docs():
    ingest()
    hits = retrieve("checkout-api 500 after latest deploy database timeout rollback policy")
    assert hits, "Chroma retrieve must return documents"
    ids = " ".join(h["id"].lower() for h in hits)
    titles = " ".join((h.get("title") or "").lower() for h in hits)
    blob = ids + " " + titles
    assert any("checkout-500" in h["id"] or "checkout-500" in (h.get("title") or "") for h in hits)
    assert "rollback" in blob or any("deployment-rollback" in h["id"] for h in hits)
    assert any(
        "deployment-rollback-policy" in h["id"]
        or "checkout-500-runbook" in h["id"]
        or "database-timeout-runbook" in h["id"]
        for h in hits
    )
