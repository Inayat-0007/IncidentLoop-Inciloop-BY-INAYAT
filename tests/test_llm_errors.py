from __future__ import annotations

import os

os.environ.setdefault("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
os.environ["DEVOPSPILOT_FORCE_HEURISTIC"] = "1"

import pytest
from backend.errors import LlmError
from backend.llm import parse_json_object
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


def test_investigate_maps_missing_gemini_to_503(client: TestClient, monkeypatch):
    async def boom(*_args, **_kwargs):
        raise LlmError(503, "llm_unavailable", "GEMINI_API_KEY is not set")

    monkeypatch.setattr("backend.graph.workflow.run_investigation", boom)
    r = client.post("/investigate", json={"prompt": "checkout-api 500 after deploy"})
    assert r.status_code == 503
    assert r.json()["code"] == "llm_unavailable"


def test_parse_json_object_strips_fences():
    data = parse_json_object('```json\n{"recommendation":"ESCALATE","ok":true}\n```')
    assert data["recommendation"] == "ESCALATE"


def test_parse_json_object_python_dict():
    data = parse_json_object("{'recommendation': 'ESCALATE', 'ok': True}")
    assert data["recommendation"] == "ESCALATE"
    assert data["ok"] is True
