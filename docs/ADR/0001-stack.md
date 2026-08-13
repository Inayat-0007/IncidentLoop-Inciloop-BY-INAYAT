# ADR 0001 — DevOpsPilot Python multi-agent stack

- Status: Accepted
- Date: 2026-08-13

## Context

The repo previously pinned TypeScript / Next.js / Hono / Postgres for an incident-loop console (IncidentLoop). The interview product is **DevOpsPilot**: a lightweight multi-agent incident and release assistant with RAG, mock production tools, an AgentOps dashboard, and pytest evaluation.

Those two products cannot share one stack without lying in `AGENTS.md`.

## Decision

Replace the Node pin with:

- Python 3.12 + FastAPI + Pydantic
- LangGraph (six nodes, one LLM)
- ChromaDB for RAG with **deterministic embeddings** so CI works without model downloads or paid APIs
- Heuristic decision engine is **TEST/CI only** (`DEVOPSPILOT_FORCE_HEURISTIC=1`). Live `POST /investigate` requires Gemini; if Gemini fails, return 502/503 — never a silent production fallback that fabricates ROLLBACK.
- Vite + React for AgentOps
- File/SQLite memory (not Postgres) for MVP
- Markdown knowledge corpus (not PDF) for ingest simplicity and git review

Remove unused Node/Next/Hono apps so the repository is one coherent product.

## Consequences

- CI is pytest + ruff, not pnpm.
- Agents must not reintroduce Hono/Next/Drizzle.
- Rollback remains a **human-authorized** mutation; the graph only recommends.
- CI scores the deterministic heuristic policy. Live Gemini is demo/manual, not a CI fallback.
