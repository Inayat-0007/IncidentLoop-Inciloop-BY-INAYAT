# DevOpsPilot

Multi-agent **production incident and release assistant** (interview MVP).

**PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY**

Lightweight agents investigate production incidents from **company-exported files** (or optional HTTP/GitHub), retrieve runbooks and past incidents (RAG), use engineering tools (metrics, logs, releases), emit a structured recommendation (`ROLLBACK` | `INVESTIGATE` | `NO_ACTION` | `ESCALATE`), and verify outcome after a **human-authorized** rollback.

Origin: [https://github.com/Inayat-0007/IncidentLoop-Inciloop-BY-INAYAT.git](https://github.com/Inayat-0007/IncidentLoop-Inciloop-BY-INAYAT.git)

This repository keeps the 2026 vibe-coding harness (`VIBE_CODING_STARTER_PACK_2026.md`, `AGENTS.md`, contracts, CI) but the product is DevOpsPilot — not a Next.js/Hono incident console.

**First-time setup (env, ports, routes, checklist):** [`docs/BEFORE_FIRST_RUN.md`](docs/BEFORE_FIRST_RUN.md).

## Company data (default live path)

Set `DATA_SOURCE=files` (default in `.env.example`). Drop three exports into `data/company/`:

- `metrics.json` — `{service, error_rate, latency_ms, status}` or Prometheus `{data: {result: ...}}`
- `logs.jsonl` or `logs.json`
- `releases.json` — `{version, deployed_at, previous_version, rollback_available}`

If those files are missing, the API loads `data/company/sample/` and sets `data_mode: sample_bundle` (loud badge). Sample is anonymized from a public GitLab.com database incident pattern (`data/company/sample/SOURCE.md`).

Other modes: `http` (`METRICS_URL`, `LOGS_URL`, `RELEASES_URL`), `github` (`GITHUB_REPO` + optional `GITHUB_TOKEN` for real GitHub releases/tags; metrics/logs still from files), `sim` (**pytest/CI only**).

This is **not** Datadog or Kubernetes. Rollback never runs from the graph. Execute requires Bearer `ROLLBACK_TOKEN` + `authorized: true` + the policy gate. Without `ROLLBACK_WEBHOOK_URL`, HTTP/GitHub execute returns **409** (`no real rollback endpoint configured`). Files mode may append `data/company/rollback_events.json` and set `desired_version` — still not a cluster mutate.

Drop real runbooks as `.md` into `knowledge/` and restart (ingest on startup). Do not commit secrets or PII log dumps.

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

Open `http://localhost:5173`. Default prompt matches the sample bundle (web-api after deploy). Swap in your three files under `data/company/` for a real investigate.

## Docker

```powershell
docker compose up --build
```

API + UI: `http://localhost:8000`

## Demo script

```powershell
python scripts/demo.py
```

Expected: recommendation `ROLLBACK` with evidence → authorized rollback → **sim store** recovered (this script forces `DATA_SOURCE=sim`). Company-file execute does not invent 1.1% health.

## LLM keys (required for live investigate)

Set `GEMINI_API_KEY` in `.env` (never commit it). Docker Compose passes `GEMINI_MODEL` through. If Gemini is down, missing, 404, or quota-limited, `POST /investigate` returns **502/503** with `error`, `code`, `detail` — not a fake `ROLLBACK`.

`DEVOPSPILOT_FORCE_HEURISTIC=1` is **pytest/CI only**.

## Evaluation scoring

CI runs the ~20 fixed scenarios against the **heuristic policy** (no Gemini). After those runs, pytest prints:

- **decision accuracy %** (must be 100% on heuristic fixtures)
- **tool-call correctness** (expected tools present: metrics, logs, RAG, latest release)
- **RAG relevance** (checkout-500 / rollback policy doc ids or keywords hit)
- **latency** (recorded in ms; no fake SLO fail unless a case is wildly slow)

Live Gemini is **demo/manual** — CI does not call Gemini and does not treat it as a production fallback.

## Resume bullet

Built DevOpsPilot, a Python/FastAPI LangGraph multi-agent assistant that investigates incidents from exported company metrics/logs/releases, RAG runbooks, evidence-based rollback recommendations, a hard human-authorization policy gate, MCP tools, and a pytest suite of 20 sim scenarios.

## Layout

```
backend/agents/   planner, incident, knowledge, release, decision, verification
backend/tools/    monitoring, logs, release + company adapter (files/http/github; sim for tests)
backend/rag/      ingest + Chroma retriever (same hash embeddings)
backend/graph/    LangGraph workflow
frontend/        Vite + React AgentOps dashboard
knowledge/       runbooks + historical incidents
mcp_server/      MCP wrappers for the same tools
tests/           ~20 fixed scenarios
```

Knowledge is **markdown** (not PDF) so ingest stays reviewable in git and CI never needs a PDF parser. See `docs/STACK.md`.
