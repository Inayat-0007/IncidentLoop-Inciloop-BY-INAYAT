# Agent operating contract

## Product

DevOpsPilot is a **multi-agent production incident and release assistant** for one simulated environment: PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY.

Pitch: investigate simulated production incidents, retrieve runbooks and past incidents (RAG), use engineering tools (metrics, logs, releases), recommend `ROLLBACK` | `INVESTIGATE` | `NO_ACTION` | `ESCALATE`, and verify outcome after an **authorized** rollback.

Details: `docs/PRD.md`.

Non-goals: real Kubernetes control plane, public status page, on-call scheduling, auto-rollback without a human, a monitoring SaaS, Slack/PagerDuty writes.

**Simulated production only.** Mock metrics/logs/releases are in-process. Do not treat this as a live cluster manager.

## Stack (pinned)

Defined in `docs/STACK.md` and `docs/ADR/0001-stack.md`. Do not invent libraries. Allowed packages: `ALLOWED_DEPS.md`.

- Python **3.12**, FastAPI, Pydantic, LangGraph, LangChain, ChromaDB, httpx
- LLM: **Gemini required** for live `POST /investigate` (`GEMINI_API_KEY`). `DEVOPSPILOT_FORCE_HEURISTIC=1` is **test/CI only** — never a silent production fallback that fabricates ROLLBACK. If Gemini fails, the API returns 502/503 (`error`, `code`, `detail`).
- React (Vite + TypeScript) AgentOps dashboard
- MCP server wrapping the same tools
- Docker Compose
- pytest evaluation (~20 fixed scenarios)

## Layout

- `backend/` — FastAPI, agents, tools, RAG, memory, graph
- `frontend/` — Vite React AgentOps UI
- `knowledge/` — runbooks and historical incidents (markdown; ingest supports `.md`)
- `mcp_server/` — MCP tools over the same mock production APIs
- `tests/` — pytest scenarios
- `contracts/` — OpenAPI
- `docs/` — PRD, C4, ADR, specs, threat model

The previous Node/Next/Hono IncidentLoop apps are **removed**. Do not resurrect Express, Nest, Next.js, or Hono.

## Commands (exact)

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ruff check backend mcp_server tests
pytest
python scripts/verify_allowed_deps.py
python -m uvicorn backend.main:app --reload --port 8000
```

Frontend (optional local): `cd frontend && npm install && npm run dev`

CI runs `ruff check`, `pytest`, `python scripts/verify_allowed_deps.py` on Python 3.12.

## Source of truth

- API: `contracts/openapi.yaml`
- Data: `docs/DATA_MODEL.md` (JSON/SQLite file store + Chroma persist)
- Decisions: `docs/ADR/`
- Specs: `docs/specs/`
- Threats: `docs/THREAT_MODEL.md`

## Invariants (never violate)

- Authz on every **mutating** route (`POST /incidents/{id}/rollback`, `POST /api/releases/rollback`)
- Recommendation vs execution are separate: **never** execute rollback without explicit user authorization AND evidence threshold AND release exists AND rollback target exists; otherwise `ESCALATE TO HUMAN`
- No new dependencies without `ALLOWED_DEPS.md` + registry check
- No secrets in source, logs, or client bundles
- Do not “fix” failing tests by deleting assertions or skipping the policy gate
- One endpoint at a time unless the human expands the spec

## Workflow

- Read the spec and ADR for the area before editing
- Plan under `.cursor/plans/` or `docs/specs/` for anything >1 file
- pytest + ruff before claiming done
- Small diffs; no drive-by refactors
- After repeating a mistake twice, update a rule or skill

## PR

- Conventional commits: `feat|fix|chore|docs|refactor|test`
- Title: `[<area>] <imperative>`
- Humans own `contracts/**` and `docs/ADR/**` (CODEOWNERS)
