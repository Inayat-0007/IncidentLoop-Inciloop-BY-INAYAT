from __future__ import annotations

import os

os.environ.setdefault("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
os.environ["DEVOPSPILOT_FORCE_HEURISTIC"] = "1"

import pytest
from backend.evaluation.test_cases import CASES
from backend.main import app
from backend.schemas import Recommendation
from backend.tools import sim_store
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    sim_store.reset_all()
    with TestClient(app) as c:
        yield c
    sim_store.reset_all()


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_mock_metrics_default_degraded(client: TestClient):
    r = client.get("/api/metrics")
    body = r.json()
    assert body["error_rate"] == 18.4
    assert body["latency_ms"] == 1240
    assert body["service"] == "checkout-api"


def test_mock_logs_errors(client: TestClient):
    lines = " ".join(client.get("/api/logs").json()["lines"])
    assert "PaymentService timeout" in lines
    assert "DB connection refused" in lines
    assert "checkout failed" in lines


def test_mock_latest_release(client: TestClient):
    body = client.get("/api/releases/latest").json()
    assert body["version"] == "v2.8.1"
    assert body["previous"] == "v2.8.0"


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_decision_scenarios(client: TestClient, case):
    r = client.post(
        "/investigate",
        json={"prompt": case.prompt, "scenario_id": case.scenario_id},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    rec = body["decision"]["recommendation"]
    assert rec == case.expected.value, (
        f"{case.id} expected {case.expected.value} got {rec} reason={body['decision']['reason']}"
    )
    assert isinstance(body["decision"]["evidence"], list)
    assert body["decision"]["evidence"]
    assert 0 <= body["decision"]["confidence"] <= 1
    if case.expected == Recommendation.ROLLBACK:
        assert len(body["decision"]["evidence"]) >= 3


def test_tc19_unauthorized_rollback(client: TestClient):
    inv = client.post(
        "/investigate",
        json={
            "prompt": "checkout-api 500 after latest deploy",
            "scenario_id": "tc01_checkout_after_deploy",
        },
    )
    incident_id = inv.json()["id"]
    missing = client.post(
        f"/incidents/{incident_id}/rollback",
        json={"authorized": True},
    )
    assert missing.status_code == 401
    not_explicit = client.post(
        f"/incidents/{incident_id}/rollback",
        json={"authorized": False},
        headers={"Authorization": "Bearer replace_me_with_a_local_token"},
    )
    assert not_explicit.status_code == 403


def test_tc20_demo_rollback_then_verify(client: TestClient):
    inv = client.post(
        "/investigate",
        json={
            "prompt": "checkout-api is throwing 500 after the latest deploy",
            "scenario_id": "tc01_checkout_after_deploy",
        },
    )
    assert inv.status_code == 200
    body = inv.json()
    assert body["decision"]["recommendation"] == "ROLLBACK"
    incident_id = body["id"]
    ops = client.get(f"/ops/{incident_id}")
    assert ops.status_code == 200
    names = [t["agent"] for t in ops.json()["traces"]]
    assert names == ["planner", "incident", "knowledge", "release", "decision", "verification"]
    rb = client.post(
        f"/incidents/{incident_id}/rollback",
        json={"authorized": True, "scenario_id": "tc01_checkout_after_deploy"},
        headers={"Authorization": "Bearer replace_me_with_a_local_token"},
    )
    assert rb.status_code == 200, rb.text
    metrics = rb.json()["verification"]["metrics"]
    assert metrics["error_rate"] == 1.1
    assert metrics["latency_ms"] == 210
    live = client.get("/api/metrics", params={"scenario_id": "tc01_checkout_after_deploy"})
    assert live.json()["error_rate"] == 1.1


def test_policy_blocks_rollback_on_investigate_incident(client: TestClient):
    inv = client.post(
        "/investigate",
        json={"prompt": "unrelated errors", "scenario_id": "tc02_unrelated_errors"},
    )
    incident_id = inv.json()["id"]
    rb = client.post(
        f"/incidents/{incident_id}/rollback",
        json={"authorized": True},
        headers={"Authorization": "Bearer replace_me_with_a_local_token"},
    )
    assert rb.status_code == 409


def test_get_incident_404(client: TestClient):
    r = client.get("/incidents/does-not-exist")
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
