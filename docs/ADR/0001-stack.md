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
- Heuristic decision engine when no `GEMINI_API_KEY` / `OPENAI_API_KEY` / Azure credentials are set
- Vite + React for AgentOps
- File/SQLite memory (not Postgres) for MVP
- Markdown knowledge corpus (not PDF) for ingest simplicity and git review

Remove unused Node/Next/Hono apps so the repository is one coherent product.

## Consequences

- CI is pytest + ruff, not pnpm.
- Agents must not reintroduce Hono/Next/Drizzle.
- Rollback remains a **human-authorized** mutation; the graph only recommends.
