from __future__ import annotations

import os

os.environ.setdefault("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
os.environ["DEVOPSPILOT_FORCE_HEURISTIC"] = "1"

import pytest
from backend.errors import LlmError
from backend.llm import _map_gemini_exc, _model_chain, parse_json_object
from backend.main import app
from backend.tools import sim_store
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    sim_store.reset_all()
    with TestClient(app) as c:
        yield c
    sim_store.reset_all()


def test_investigate_maps_gemini_failure_to_502(client: TestClient, monkeypatch):
    async def boom(*_args, **_kwargs):
        raise LlmError(502, "llm_upstream", "Gemini model not found (check GEMINI_MODEL)")

    monkeypatch.setattr("backend.graph.workflow.run_investigation", boom)
    r = client.post("/investigate", json={"prompt": "checkout-api 500 after deploy"})
    assert r.status_code == 502
    body = r.json()
    assert body["code"] == "llm_upstream"
    assert body["error"] == "llm_upstream"
    assert "Gemini" in body["detail"]
    assert "ROLLBACK" not in body["detail"]
    assert "recommendation" not in body


def test_investigate_maps_quota_to_503(client: TestClient, monkeypatch):
    async def boom(*_args, **_kwargs):
        raise LlmError(503, "llm_quota", "Gemini quota or rate limit")

    monkeypatch.setattr("backend.graph.workflow.run_investigation", boom)
    r = client.post("/investigate", json={"prompt": "checkout-api 500 after deploy"})
    assert r.status_code == 503
    body = r.json()
    assert body["code"] == "llm_quota"
    assert body["error"] == "llm_quota"
    assert "quota" in body["detail"].lower()
    assert "recommendation" not in body


def test_map_gemini_exc_429_status():
    exc = RuntimeError("rate limited")
    exc.response = type("R", (), {"status_code": 429})()
    mapped = _map_gemini_exc(exc)
    assert mapped.status == 503
    assert mapped.code == "llm_quota"


def test_map_gemini_exc_quota_in_text():
    mapped = _map_gemini_exc(RuntimeError("Error calling model: 429 You exceeded your current quota"))
    assert mapped.status == 503
    assert mapped.code == "llm_quota"


def test_map_gemini_exc_resource_exhausted():
    class ResourceExhausted(Exception):
        pass

    mapped = _map_gemini_exc(ResourceExhausted("Too many requests"))
    assert mapped.code == "llm_quota"
    assert mapped.status == 503


def test_model_chain_includes_fallbacks(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite,gemini-2.0-flash")
    assert _model_chain() == [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
    ]


def test_investigate_maps_missing_gemini_to_503(client: TestClient, monkeypatch):
    async def boom(*_args, **_kwargs):
        raise LlmError(503, "llm_unavailable", "GEMINI_API_KEY is not set")

    monkeypatch.setattr("backend.graph.workflow.run_investigation", boom)
    r = client.post("/investigate", json={"prompt": "checkout-api 500 after deploy"})
    assert r.status_code == 503
    assert r.json()["code"] == "llm_unavailable"


def test_map_gemini_exc_not_found_underscore():
    mapped = _map_gemini_exc(
        RuntimeError(
            "Error calling model (NOT_FOUND): 404 NOT_FOUND. "
            "{'error': {'code': 404, 'status': 'NOT_FOUND'}}"
        )
    )
    assert mapped.status == 502
    assert mapped.code == "llm_upstream"
    assert "not found" in mapped.detail.lower()


def test_parse_json_object_strips_fences():
    data = parse_json_object('```json\n{"recommendation":"ESCALATE","ok":true}\n```')
    assert data["recommendation"] == "ESCALATE"


def test_parse_json_object_python_dict():
    data = parse_json_object("{'recommendation': 'ESCALATE', 'ok': True}")
    assert data["recommendation"] == "ESCALATE"
    assert data["ok"] is True


def test_use_gemini_for_core_skips_tool_nodes(monkeypatch):
    monkeypatch.setenv("DEVOPSPILOT_FORCE_HEURISTIC", "0")
    monkeypatch.setenv("GEMINI_NODES", "core")
    from backend.config import use_gemini_for

    assert use_gemini_for("planner") is True
    assert use_gemini_for("decision") is True
    assert use_gemini_for("knowledge") is False
    assert use_gemini_for("release") is False
    assert use_gemini_for("verification") is False
    assert use_gemini_for("incident") is False
