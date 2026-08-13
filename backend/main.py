from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import DATA_DIR, ROLLBACK_TOKEN, WEB_ORIGIN
from backend.memory import store as memory
from backend.policy.gate import evaluate_rollback_execution
from backend.rag.ingest import ingest
from backend.schemas import (
    Decision,
    ErrorBody,
    IncidentRecord,
    InvestigateRequest,
    MockRollbackRequest,
    RollbackRequest,
)
from backend.tools import logs as logs_tool
from backend.tools import monitoring as monitoring_tool
from backend.tools import release as release_tool


def _token_ok(authorization: str | None) -> bool:
    if not authorization:
        return False
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return False
    return authorization[len(prefix) :].strip() == ROLLBACK_TOKEN


@asynccontextmanager
async def lifespan(_app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    memory.init()
    ingest()
    yield


app = FastAPI(title="DevOpsPilot", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content=ErrorBody(code=code, message=message).model_dump())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metrics")
def api_metrics(
    scenario_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
) -> dict[str, Any]:
    return monitoring_tool.get_metrics(scenario_id, service)


@app.get("/api/logs")
def api_logs(
    scenario_id: str | None = Query(default=None),
    service: str | None = Query(default=None),
) -> dict[str, Any]:
    return logs_tool.get_logs(scenario_id, service)


@app.get("/api/releases/latest")
def api_latest_release(scenario_id: str | None = Query(default=None)) -> dict[str, Any]:
    return release_tool.get_latest_release(scenario_id)


@app.post("/api/releases/rollback")
def api_mock_rollback(
    body: MockRollbackRequest,
    authorization: str | None = Header(default=None),
) -> Any:
    if not _token_ok(authorization):
        return _error(401, "unauthorized", "Missing or invalid bearer token")
    if not body.authorized:
        return _error(403, "forbidden", "ESCALATE TO HUMAN: explicit authorized=true required")
    return release_tool.rollback_release(body.scenario_id)


@app.post("/investigate")
def investigate(body: InvestigateRequest) -> IncidentRecord:
    from backend.graph.workflow import run_investigation

    result = run_investigation(body.prompt, body.scenario_id, body.service)
    decision = Decision.model_validate(result["decision"])
    record = IncidentRecord(
        id=result["incident_id"],
        prompt=body.prompt,
        scenario_id=result["scenario_id"],
        service=result["service"],
        status="recommended",
        decision=decision,
        verification=result.get("verification") or {},
        traces=result.get("traces") or [],
        release=result.get("release") or {},
        logs=(result.get("logs") or {}).get("lines") or [],
    )
    payload = record.model_dump()
    memory.save_incident(record.id, payload)
    memory.add_conversation(record.id, "user", body.prompt)
    memory.save_recommendation(record.id, decision.model_dump())
    memory.dump_json_backup()
    return record


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> Any:
    row = memory.get_incident(incident_id)
    if not row:
        return _error(404, "not_found", "Incident not found")
    return row


@app.get("/ops/{incident_id}")
def get_ops(incident_id: str) -> Any:
    row = memory.get_incident(incident_id)
    if not row:
        return _error(404, "not_found", "Incident not found")
    traces = row.get("traces") or []
    runtime = sum(float(t.get("duration_ms") or 0) for t in traces)
    decision = row.get("decision") or {}
    return {
        "incident_id": incident_id,
        "traces": traces,
        "runtime_ms": runtime,
        "recommendation": decision.get("recommendation"),
        "confidence": decision.get("confidence"),
        "status": row.get("status"),
        "docs_retrieved": [
            d
            for t in traces
            for d in (t.get("docs_retrieved") or [])
        ],
        "tools_used": [tool for t in traces for tool in (t.get("tools_used") or [])],
        "service": row.get("service"),
        "decision": decision,
        "verification": row.get("verification"),
    }


@app.post("/incidents/{incident_id}/rollback")
def execute_rollback(
    incident_id: str,
    body: RollbackRequest,
    authorization: str | None = Header(default=None),
) -> Any:
    row = memory.get_incident(incident_id)
    if not row:
        return _error(404, "not_found", "Incident not found")
    decision = Decision.model_validate(row["decision"])
    scenario_id = body.scenario_id or row.get("scenario_id")
    ok, message = evaluate_rollback_execution(
        authorized=body.authorized,
        token_ok=_token_ok(authorization),
        decision=decision,
        scenario_id=scenario_id,
    )
    if not _token_ok(authorization):
        return _error(401, "unauthorized", message)
    if not body.authorized:
        return _error(403, "forbidden", message)
    if not ok:
        return _error(409, "policy_denied", message)

    mutated = release_tool.rollback_release(scenario_id)
    metrics = monitoring_tool.get_metrics(scenario_id, row.get("service"))
    row["status"] = "verified"
    row["verification"] = {
        "metrics": metrics,
        "recovered": True,
        "status": "healthy",
        "note": "Authorized rollback executed; mock production recovered.",
        "release_after": mutated.get("release"),
    }
    memory.save_incident(incident_id, row)
    memory.mark_resolved(incident_id)
    memory.dump_json_backup()
    return row


_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="assets")

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
