# DevOpsPilot

Multi-agent **production incident and release assistant** (interview MVP).

**PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY**

Lightweight agents investigate a **simulated** production incident, retrieve runbooks and past incidents (RAG), use engineering tools (metrics, logs, releases), emit a structured recommendation (`ROLLBACK` | `INVESTIGATE` | `NO_ACTION` | `ESCALATE`), and verify health after a **human-authorized** rollback.

Origin: [https://github.com/Inayat-0007/IncidentLoop-Inciloop-BY-INAYAT.git](https://github.com/Inayat-0007/IncidentLoop-Inciloop-BY-INAYAT.git)

This repository keeps the 2026 vibe-coding harness (`VIBE_CODING_STARTER_PACK_2026.md`, `AGENTS.md`, contracts, CI) but the product is DevOpsPilot — not a Next.js/Hono incident console.

## Simulated production (honest disclaimer)

Metrics, logs, and releases are **in-process mocks**. Nothing talks to a real cluster, Kubernetes, or vendor APM. Rollback only mutates mock state (error_rate ~1.1, latency ~210).

## How to run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
pytest
python -m uvicorn backend.main:app --reload --port 8000
```

AgentOps UI (second terminal):

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Default prompt is checkout-api 500 after latest deploy.

## Docker

```powershell
docker compose up --build
```

API + UI: `http://localhost:8000`

## Demo script

```powershell
python scripts/demo.py
```

Expected: recommendation `ROLLBACK` with evidence → authorized rollback → metrics recovered.

## LLM keys (optional)

Set `GEMINI_API_KEY` or `OPENAI_API_KEY` or Azure `AZURE_*` in `.env`. If unset, a **deterministic heuristic** still produces the demo decision so tests and Docker work without paid APIs.

## Resume bullet

Built DevOpsPilot, a Python/FastAPI LangGraph multi-agent assistant that investigates simulated incidents with RAG runbooks, evidence-based rollback recommendations, a hard human-authorization policy gate, MCP tools, and a pytest suite of 20 scenarios.

## Layout

```
backend/agents/   planner, incident, knowledge, release, decision, verification
backend/tools/    monitoring, logs, release (mock production)
backend/rag/      ingest + retriever (markdown → Chroma / keyword)
backend/graph/    LangGraph workflow
frontend/        Vite + React AgentOps dashboard
knowledge/       runbooks + historical incidents
mcp_server/      MCP wrappers for the same tools
tests/           ~20 fixed scenarios
```

Knowledge is **markdown** (not PDF) so ingest stays reviewable in git and CI never needs a PDF parser. See `docs/STACK.md`.
