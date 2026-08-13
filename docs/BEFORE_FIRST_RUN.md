# Before first run — DevOpsPilot

How to set up **this** repository before you start the API or UI. Paths, env names, and HTTP routes below are taken from the code, not a generic template.

## 1. What this system is

DevOpsPilot is a **multi-agent production incident and release assistant** for **one simulated environment**: PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY. A FastAPI service runs a LangGraph of six agents that read **in-process mock** metrics, logs, and releases, retrieve markdown runbooks/incidents (RAG), and emit `ROLLBACK` | `INVESTIGATE` | `NO_ACTION` | `ESCALATE`. A human must authorize rollback; the graph never executes it. This is **not** a Kubernetes control plane, live cluster manager, Datadog, or GitHub deploy API. Rollback only mutates mock state (healthy band: `error_rate` 1.1, `latency_ms` 210).

## 2. Architecture

```mermaid
flowchart TB
  subgraph ui ["AgentOps UI"]
    React["Vite React frontend/<br/>localhost:5173"]
  end

  subgraph api ["FastAPI backend.main:app"]
    Routes["GET /health<br/>POST /investigate<br/>GET /incidents/id<br/>POST /incidents/id/rollback<br/>GET /ops/id<br/>GET /api/metrics|logs|releases/latest<br/>POST /api/releases/rollback"]
    CORS["CORS: WEB_ORIGIN + localhost:5173"]
  end

  subgraph graph ["LangGraph backend/graph/workflow.py"]
    P[planner]
    I[incident]
    K[knowledge]
    R[release]
    D[decision]
    V[verification]
    P --> I --> K --> R --> D --> V
  end

  subgraph tools ["Mock production in-process"]
    Mon["tools/monitoring.py"]
    Logs["tools/logs.py"]
    Rel["tools/release.py"]
    Sim["tools/sim_store.py"]
    Mon --> Sim
    Logs --> Sim
    Rel --> Sim
  end

  subgraph rag ["Knowledge"]
    MD["knowledge/**/*.md"]
    Ingest["rag/ingest.py on API lifespan"]
    Chroma["Chroma persist CHROMA_PATH"]
    Retr["rag/retriever.py keyword over markdown"]
    MD --> Ingest --> Chroma
    MD --> Retr
  end

  subgraph mem ["Memory"]
    SQLite["data/memory.sqlite"]
    JSON["data/memory.json backup"]
  end

  subgraph traces ["AgentOps"]
    Tr["IncidentRecord.traces + GET /ops/{id}"]
  end

  subgraph mcp ["Parallel tool surface"]
    MCP["mcp_server/server.py FastMCP stdio"]
  end

  React -->|"Vite proxy /investigate /incidents /ops /api /health"| Routes
  Routes -->|"run_investigation"| P
  I --> Mon
  I --> Logs
  K --> Retr
  R --> Rel
  V --> Mon
  Routes -->|"authorized rollback"| Rel
  Routes --> SQLite
  Routes --> JSON
  graph --> Tr
  MCP --> Mon
  MCP --> Logs
  MCP --> Rel
```

Docker Compose is **one** `api` service on port 8000. If `frontend/dist` exists (image build), FastAPI also serves the SPA at `/`. There is no second product microservice.

## 3. File-path map

| Path | Role |
|---|---|
| `AGENTS.md` | Agent operating contract: stack, invariants, commands |
| `README.md` | Short run instructions |
| `.env.example` | Env names to copy locally; never commit `.env` |
| `.python-version` | Pins **3.12** |
| `ALLOWED_DEPS.md` | Allowed PyPI/npm names |
| `requirements.txt` | Pinned Python deps |
| `docker-compose.yml` | Single `api` service, `8000:8000`, volume `pilot-data` |
| `Dockerfile` | Multi-stage: Node builds UI, Python 3.12 runs uvicorn as `appuser` |
| `backend/main.py` | FastAPI app, CORS, routes, lifespan ingest |
| `backend/config.py` | `load_dotenv()`, paths, `ROLLBACK_TOKEN`, `WEB_ORIGIN`, heuristic flag |
| `backend/schemas.py` | Pydantic request/decision/incident/trace models |
| `backend/llm.py` | Optional Gemini/Azure/OpenAI; heuristic if no key |
| `backend/graph/workflow.py` | LangGraph: planner → incident → knowledge → release → decision → verification |
| `backend/agents/planner.py` | Extract service + scenario; numbered plan (no rollback) |
| `backend/agents/incident.py` | Calls mock metrics + logs |
| `backend/agents/knowledge.py` | RAG retrieve |
| `backend/agents/release.py` | Latest mock release |
| `backend/agents/decision.py` | Heuristic recommendation (+ optional LLM restatement) |
| `backend/agents/verification.py` | Re-reads metrics; does **not** execute rollback |
| `backend/tools/sim_store.py` | In-memory scenario snapshots |
| `backend/tools/monitoring.py` | `get_metrics` |
| `backend/tools/logs.py` | `get_logs` |
| `backend/tools/release.py` | `get_latest_release` / `rollback_release` |
| `backend/rag/ingest.py` | Load `knowledge/` `.md`/`.txt` into Chroma (hash embeddings) |
| `backend/rag/retriever.py` | Keyword rank over markdown (runtime retrieve) |
| `backend/memory/store.py` | SQLite + JSON backup |
| `backend/policy/gate.py` | Rollback execution gate |
| `backend/evaluation/test_cases.py` | ~20 fixed eval scenarios |
| `frontend/src/App.tsx` | AgentOps UI: investigate + authorize rollback |
| `frontend/vite.config.ts` | Port 5173; proxy to `http://127.0.0.1:8000` |
| `frontend/package.json` | Vite + React 19 scripts |
| `knowledge/runbooks/` | Checkout 500 + DB timeout runbooks |
| `knowledge/incidents/` | Historical incident markdown |
| `knowledge/policies/deployment-rollback-policy.md` | Rollback policy text for RAG |
| `mcp_server/server.py` | FastMCP stdio tools over the same mocks |
| `.cursor/mcp.json` | Cursor MCP: `devopspilot` stdio + optional GitHub/GitLab npx servers |
| `contracts/openapi.yaml` | API source of truth |
| `contracts/asyncapi.yaml` | Async contract stub (not a live broker) |
| `scripts/demo.py` | In-process TestClient killer demo |
| `scripts/verify_allowed_deps.py` | CI dep allowlist check (uses httpx) |
| `scripts/check-no-secrets.sh` / `.mjs` | Secret-scan helpers (leftover vibe-pack scripts) |
| `tests/test_scenarios.py` | Scenario suite |
| `tests/test_policy.py` | Unauthorized / policy-denied rollback |
| `tests/test_rag.py` | Ingest/retrieve |
| `.github/workflows/ci.yml` | Python 3.12: ruff, pytest, allowlist |
| `.github/workflows/sast.yml` | Semgrep |
| `.github/workflows/secret-scan.yml` | Gitleaks |
| `docs/PRD.md` | Product requirements |
| `docs/STACK.md` | Pinned stack |
| `docs/DATA_MODEL.md` | SQLite/JSON + Chroma + sim |
| `docs/ADR/0001-stack.md` | Stack ADR |
| `docs/THREAT_MODEL.md` | Abuse cases |
| `docs/SECURITY.md` | Secrets / rollback token |
| `docs/API.md` | Route list pointing at OpenAPI |
| `docs/DEPRECATED_NODE.md` | Old Node/Next/Hono apps are gone |
| `data/README.md` | Placeholder; persist files are gitignored |
| `VIBE_CODING_STARTER_PACK_2026.md` | Harness notes (lefthook mentioned there, **not** installed here) |

## 4. Killer-demo data flow (real routes)

Default UI prompt (`frontend/src/App.tsx`): checkout-api 500 after latest deploy. Planner maps that to scenario `tc01_checkout_after_deploy` (`backend/agents/planner.py`).

1. **User prompt** → `POST /investigate` JSON `{ "prompt": "...", "scenario_id"?: string, "service"?: string }` (`InvestigateRequest` requires `prompt`).
2. **Planner** (`planner` node) — extract service/scenario; optional LLM plan; **does not** call rollback.
3. **Incident** — in-process `monitoring.get_metrics` + `logs.get_logs` (same data as `GET /api/metrics` and `GET /api/logs`).
4. **Knowledge** — `rag.retrieve` over `knowledge/**/*.md` (also ingested to Chroma on API startup).
5. **Release** — in-process `release.get_latest_release` (same as `GET /api/releases/latest`).
6. **Decision** — heuristic (and optional LLM one-liner). Killer path: `recommendation: "ROLLBACK"`, confidence ≥ 0.7, ≥ 3 evidence bullets.
7. **Verification** (graph) — reads metrics **again**; after investigate, sim is still degraded → `status: "pending_authorization"`. Graph **does not** call rollback tools.
8. Record saved: SQLite `data/memory.sqlite` + `data/memory.json`. Response is `IncidentRecord` (`id`, `prompt`, `scenario_id`, `service`, `status`, `decision`, `verification`, `traces`, `release`, `logs`).
9. **Human-authorized execute** → `POST /incidents/{incident_id}/rollback` with `Authorization: Bearer $ROLLBACK_TOKEN` and JSON `{ "authorized": true, "scenario_id"?: "..." }`. Policy gate (`backend/policy/gate.py`) requires token, `authorized=true`, recommendation `ROLLBACK`, confidence ≥ 0.7, ≥ 3 evidence items, current release, rollback target. Then `rollback_release` mutates sim.
10. Response incident `status: "verified"`; `verification.metrics` recovered (`error_rate` 1.1, `latency_ms` 210). Optional: `GET /ops/{incident_id}` for traces; `GET /incidents/{incident_id}` for stored record.

Direct mock mutate (same token + `authorized: true`): `POST /api/releases/rollback` — **not** used by the AgentOps UI; UI uses `/incidents/{id}/rollback`.

`scripts/demo.py` drives this with FastAPI `TestClient` (no listening server required). It posts `tc01_checkout_after_deploy` and Bearer `replace_me_with_a_local_token`.

## 5. Connectivity matrix

| From | To | How |
|---|---|---|
| Browser `http://localhost:5173` | FastAPI `127.0.0.1:8000` | Vite **dev proxy** for `/investigate`, `/incidents`, `/ops`, `/api`, `/health` (`frontend/vite.config.ts`). UI `fetch` uses **relative** paths; there is **no** `VITE_API_*` env. |
| Browser origin vs API | CORS | `WEB_ORIGIN` plus hardcoded `http://localhost:5173` and `http://127.0.0.1:5173`. Methods GET/POST/OPTIONS. Headers `Authorization`, `Content-Type`. `allow_credentials=False`. |
| Docker UI | Same origin `:8000` | Compose sets `WEB_ORIGIN=http://localhost:8000`. Image copies `frontend/dist`; FastAPI mounts `/assets` and `GET /`. |
| Graph agents | Mock tools | **In-process Python**, not HTTP. `/api/*` is the HTTP face of the same functions. |
| RAG ingest | Disk | `CHROMA_PATH` default `./data/chroma` (`backend/config.py`). Collection name `devopspilot`. |
| Runtime retrieve | Markdown files | `retriever.py` scores `knowledge/` on disk (does not query Chroma at retrieve time). |
| Memory | Disk | `DATA_DIR/memory.sqlite` and `DATA_DIR/memory.json`. Default `DATA_DIR=./data`. |
| MCP product server | Same mocks | **stdio** via `python mcp_server/server.py` (`mcp.run()`). Cursor: `.cursor/mcp.json` server `devopspilot`. **No HTTP MCP port** in this repo. |
| Cursor GitHub/GitLab MCP | External | Optional `npx` servers; tokens `${env:GITHUB_TOKEN}` / `${env:GITLAB_TOKEN}`. **Not** used by FastAPI or the demo. |
| LLM | Vendor APIs | Only if keys set and `DEVOPSPILOT_FORCE_HEURISTIC` is not truthy. Graph still works without them. |

## 6. Environment variables

Copy, then edit locally. **Never commit `.env`.**

```powershell
Copy-Item .env.example .env
```

From `.env.example` (and a few names read in code but not listed there):

| Name | Required? | Used where | Notes |
|---|---|---|---|
| `ROLLBACK_TOKEN` | **Yes for mutations** | `backend/config.py` → `POST /incidents/{id}/rollback`, `POST /api/releases/rollback` | Default in code if unset: `replace_me_with_a_local_token` (same as `.env.example` and `scripts/demo.py`). Generate a local random string for anything beyond local demo. |
| `WEB_ORIGIN` | Optional | CORS in `backend/main.py` | Default `http://localhost:5173`. Docker Compose overrides to `http://localhost:8000`. |
| `DATA_DIR` | Optional | config, memory, ingest | Default `./data` |
| `CHROMA_PATH` | Optional | `rag/ingest.py` | Default `./data/chroma` |
| `DEVOPSPILOT_FORCE_HEURISTIC` | Optional | `backend/llm.py` via `FORCE_HEURISTIC` | `1` / `true` / `True` skips LLM even if keys exist. CI and Docker default **on**. Local `.env.example` is `0`. |
| `GEMINI_API_KEY` | Optional | `llm.py` (first if set) | Heuristic if empty |
| `OPENAI_API_KEY` | Optional | `llm.py` (if no Gemini and no Azure) | Heuristic if empty |
| `AZURE_OPENAI_API_KEY` | Optional | `llm.py` (after Gemini, before OpenAI) | Needs endpoint + deployment to actually call |
| `AZURE_OPENAI_ENDPOINT` | Optional | `llm.py` | |
| `AZURE_OPENAI_DEPLOYMENT` | Optional | `llm.py` | |
| `AZURE_OPENAI_API_VERSION` | Optional | `llm.py` | Default `2024-10-21` |
| `APP_ENV` | Documented only | **Not read** by Python | Placeholder in `.env.example` |
| `API_HOST` | Documented only | **Not read** by Python | Uvicorn host comes from the CLI (`127.0.0.1` local / `0.0.0.0` Docker) |
| `API_PORT` | Documented only | **Not read** by Python | Use `--port 8000` |
| `GITHUB_TOKEN` | Optional OS env | `.cursor/mcp.json` only (commented in `.env.example`) | Not a product API key |
| `GITLAB_TOKEN` | Optional OS env | `.cursor/mcp.json` only | Not a product API key |

Also used in code, **not** in `.env.example`:

| Name | Default | Where |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.0-flash` | `backend/llm.py` |
| `OPENAI_MODEL` | `gpt-4o-mini` | `backend/llm.py` |

`python-dotenv` loads `.env` from the process cwd when `backend.config` is imported.

## 7. Ports

| What | Port | Mapping |
|---|---|---|
| FastAPI / uvicorn | **8000** | Local: `--port 8000`. Docker Compose: `"8000:8000"`. Image `EXPOSE 8000`. |
| Vite AgentOps | **5173** | `frontend/vite.config.ts` `server.port`. Not published in Compose. |
| MCP | none | stdio |

## 8. Prerequisites

- **Python 3.12 preferred.** CI (`.github/workflows/ci.yml`) and `.python-version` pin **3.12**. Local **3.14** may work for a sanity import; do not treat it as the supported pin.
- **pip** + **venv**
- **Node.js + npm** only if you run `frontend/` (`npm install` / `npm run dev`). Docker builds the UI inside the image.
- **Docker / Compose** optional (`docker compose up --build`)
- Git

Windows PowerShell: if `Activate.ps1` is blocked, `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.venv\Scripts\python.exe` without activating.

## 9. Ordered first-run checklist (Windows PowerShell)

1. Clone (or open) the repo.

```powershell
git clone https://github.com/Inayat-0007/IncidentLoop-Inciloop-BY-INAYAT.git
cd "IncidentLoop Inciloop"   # or your local folder name
```

2. Virtualenv + deps.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Env file.

```powershell
Copy-Item .env.example .env
# Optional: set ROLLBACK_TOKEN to a random string; keep demo default if you will run scripts/demo.py unchanged
```

4. **Knowledge ingest** — **no separate CLI.** FastAPI `lifespan` in `backend/main.py` runs `memory.init()` then `ingest()`. Pytest/`scripts/demo.py` also import the app and trigger lifespan via TestClient. Editing `knowledge/**/*.md` is the source of truth; `data/chroma/` is generated and gitignored.

5. Tests + quality (same as CI, minus GitHub-only SAST/gitleaks).

```powershell
ruff check backend mcp_server tests scripts
pytest
python scripts/verify_allowed_deps.py
```

6. Start API (terminal 1).

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

7. Start frontend (terminal 2, optional if you only curl the API).

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Rollback token field defaults to `replace_me_with_a_local_token` (must match `ROLLBACK_TOKEN`).

8. Demo script (does **not** need uvicorn; uses TestClient). From repo root with venv active:

```powershell
python scripts/demo.py
```

Expect: `recommendation: ROLLBACK`, evidence lines, `after rollback: ... error_rate 1.1 ... latency_ms 210`, `demo ok`.

9. Docker alternative (heuristic forced; LLM keys optional).

```powershell
docker compose up --build
```

Then use `http://localhost:8000` (API + built UI). Volume `pilot-data` → `/app/data`. Image user is `appuser` (uid 10001).

Optional MCP (Cursor): `python mcp_server/server.py` as configured in `.cursor/mcp.json` (stdio). Not required for the killer demo.

## 10. Verify wiring (no guessing)

PowerShell (`curl.exe` to avoid the `curl` alias):

```powershell
curl.exe -s http://127.0.0.1:8000/health
```

Expected: `{"status":"ok"}`

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/investigate -H "Content-Type: application/json" -d "{\"prompt\":\"checkout-api is throwing 500 after the latest deploy\",\"scenario_id\":\"tc01_checkout_after_deploy\"}"
```

Expected JSON fields (Pydantic `IncidentRecord`): `id`, `prompt`, `scenario_id`, `service`, `status` (`recommended`), `decision` (`service`, `observed_metrics`, `evidence`, `recommendation`, `reason`, `confidence`), `verification`, `traces` (agents `planner`, `incident`, `knowledge`, `release`, `decision`, `verification`), `release`, `logs`. For this scenario `decision.recommendation` should be `ROLLBACK`.

Mock telemetry (same sim):

```powershell
curl.exe -s "http://127.0.0.1:8000/api/metrics?scenario_id=tc01_checkout_after_deploy&service=checkout-api"
curl.exe -s "http://127.0.0.1:8000/api/logs?scenario_id=tc01_checkout_after_deploy&service=checkout-api"
curl.exe -s "http://127.0.0.1:8000/api/releases/latest?scenario_id=tc01_checkout_after_deploy"
```

Unauthorized rollback (expect `401` body `code`/`message`):

```powershell
curl.exe -s -o - -w "\nHTTP:%{http_code}\n" -X POST http://127.0.0.1:8000/incidents/does-not-exist/rollback -H "Content-Type: application/json" -d "{\"authorized\":true}"
```

Authorized path after investigate: copy `id` from investigate, then:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/incidents/REPLACE_ID/rollback -H "Content-Type: application/json" -H "Authorization: Bearer replace_me_with_a_local_token" -d "{\"authorized\":true,\"scenario_id\":\"tc01_checkout_after_deploy\"}"
```

Then `GET /incidents/{id}` and `GET /ops/{id}` (`incident_id`, `traces`, `runtime_ms`, `recommendation`, `confidence`, `status`, `docs_retrieved`, `tools_used`, `service`, `decision`, `verification`).

Via Vite: same paths on `http://localhost:5173` (proxied).

## 11. What is not wired (honest)

- No live Kubernetes, cluster, or deploy control plane.
- No Datadog / Prometheus / vendor APM — metrics are `sim_store`.
- No GitHub/GitLab **product** deploy API. Cursor MCP GitHub/GitLab entries are optional IDE servers, unused by FastAPI.
- No Slack/PagerDuty writes, on-call, public status page, or auto-rollback without a human.
- LLM is **optional**. Missing keys or `DEVOPSPILOT_FORCE_HEURISTIC=1` → deterministic heuristic (`backend/agents/decision.py`). Docker/CI force heuristic.
- Agents do not HTTP-call `/api/*`; those routes exist for humans/UI/curl/MCP-equivalent inspection.
- Chroma is written on ingest; **retrieve** is keyword-over-markdown, so a missing Chroma dir does not block investigate if `knowledge/` exists.
- `APP_ENV` / `API_HOST` / `API_PORT` in `.env.example` are unused by application code.
- `httpx` is for `scripts/verify_allowed_deps.py` (PyPI), not mock tools.
- Previous Node/Next/Hono IncidentLoop apps are **removed** (`docs/DEPRECATED_NODE.md`).

## 12. Troubleshooting

| Symptom | Reality |
|---|---|
| Looking for Express/Nest/Next/Hono | Gone. Product is FastAPI + Vite. See `docs/DEPRECATED_NODE.md`. |
| Empty RAG / missing vectors | `data/chroma/` is **gitignored**. Ingest runs on API startup (`lifespan`). Source is `knowledge/**/*.md`. Do not commit generated Chroma. |
| Docker volume / permission errors | Container runs as **`appuser`** (uid 10001). Data lives in named volume `pilot-data` at `/app/data`. Avoid bind-mounting a Windows folder as `/app/data` unless it is writable by that user. |
| “lefthook not found” | Vibe pack mentions lefthook/husky; **this repo has no lefthook config**. CI uses GitHub Actions (ruff, pytest, gitleaks, semgrep). Optional leftover: `scripts/check-no-secrets.sh`. |
| Rollback 401 | Bearer must equal `ROLLBACK_TOKEN`. UI default and demo use `replace_me_with_a_local_token`. |
| Rollback 403 | Body must include `"authorized": true`. |
| Rollback 409 `policy_denied` | Gate refused: not ROLLBACK, low confidence, few evidence bullets, or missing release/target. |
| CORS in the browser | Hit the UI on 5173 (proxy) or 8000 (Docker SPA). Custom origins: set `WEB_ORIGIN`. |
| Frontend talks to the wrong host | No API base URL env — Vite proxy must reach `127.0.0.1:8000`. Start uvicorn first. |
| pytest wants LLM | Tests set `DEVOPSPILOT_FORCE_HEURISTIC=1`. Do not skip the policy tests to “make it pass”. |
| `Activate.ps1` blocked | Use `.venv\Scripts\python.exe -m uvicorn ...` instead. |
| Python 3.14 locally vs 3.12 CI | Prefer 3.12 to match CI. |

## Real HTTP routes (inventory)

| Method | Path | Auth |
|---|---|---|
| GET | `/health` | no |
| POST | `/investigate` | no |
| GET | `/incidents/{incident_id}` | no |
| POST | `/incidents/{incident_id}/rollback` | Bearer + `authorized: true` + policy |
| GET | `/ops/{incident_id}` | no |
| GET | `/api/metrics` | no |
| GET | `/api/logs` | no |
| GET | `/api/releases/latest` | no |
| POST | `/api/releases/rollback` | Bearer + `authorized: true` |
| GET | `/` and `/assets/*` | only if `frontend/dist` exists (Docker image) |
