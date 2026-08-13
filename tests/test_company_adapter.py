from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend.schemas import Decision, Recommendation
from backend.tools import adapter
from backend.tools.adapter import NO_ROLLBACK_ENDPOINT, normalize_logs, normalize_metrics, normalize_release
from fastapi.testclient import TestClient


def _write_company(tmp: Path, *, error_rate: float = 12.7) -> None:
    (tmp / "metrics.json").write_text(
        json.dumps(
            {
                "service": "checkout-api",
                "error_rate": error_rate,
                "latency_ms": 890,
                "status": "degraded",
            }
        ),
        encoding="utf-8",
    )
    (tmp / "logs.jsonl").write_text(
        "\n".join(
            [
                "ERROR PaymentService timeout waiting for gateway",
                "ERROR DB connection refused on checkout-primary:5432",
                "ERROR checkout failed with HTTP 500",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp / "releases.json").write_text(
        json.dumps(
            {
                "version": "v9.2.1",
                "previous_version": "v9.2.0",
                "rollback_available": True,
                "deployed_at": "2026-08-13T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_normalize_flat_metrics():
    body = normalize_metrics(
        {"service": "billing", "error_rate": 9.1, "latency_ms": 400, "status": "degraded"},
        None,
    )
    assert body["error_rate"] == 9.1
    assert body["service"] == "billing"
    assert 18.4 not in body.values()


def test_normalize_prometheus_metrics():
    payload = {
        "data": {
            "result": [
                {
                    "metric": {"__name__": "http_error_ratio", "service": "web-api"},
                    "value": [1, "0.127"],
                },
                {
                    "metric": {"__name__": "request_latency_seconds", "service": "web-api"},
                    "value": [1, "0.89"],
                },
            ]
        }
    }
    body = normalize_metrics(payload, None)
    assert body["service"] == "web-api"
    assert body["error_rate"] == pytest.approx(12.7)
    assert body["latency_ms"] == pytest.approx(890)


def test_normalize_logs_shapes():
    assert normalize_logs(["ERROR boom", "INFO ok"], "svc")["lines"] == ["ERROR boom", "INFO ok"]
    assert normalize_logs({"lines": [{"message": "ERROR x"}]}, "svc")["lines"] == ["ERROR x"]


def test_normalize_release_previous_version():
    rel = normalize_release(
        {"version": "v2", "previous_version": "v1", "rollback_available": True},
        "svc",
    )
    assert rel["previous"] == "v1"
    assert rel["rollback_available"] is True
    assert rel["missing"] is False


def test_files_adapter_reads_temp_json(tmp_path: Path, monkeypatch):
    _write_company(tmp_path, error_rate=12.7)
    monkeypatch.setenv("DATA_SOURCE", "files")
    monkeypatch.setenv("COMPANY_DATA_DIR", str(tmp_path))
    metrics = adapter.get_metrics(None, None)
    assert metrics["error_rate"] == 12.7
    assert metrics["error_rate"] != 18.4
    assert metrics["data_mode"] == "company_files"
    assert metrics["badge"] == "Company files"
    logs = adapter.get_logs(None, None)
    assert any("PaymentService timeout" in ln for ln in logs["lines"])
    rel = adapter.get_latest_release(None)
    assert rel["version"] == "v9.2.1"
    assert rel["previous"] == "v9.2.0"


def test_sample_bundle_when_live_files_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "files")
    monkeypatch.setenv("COMPANY_DATA_DIR", str(tmp_path))
    metrics = adapter.get_metrics(None, None)
    assert metrics["data_mode"] == "sample_bundle"
    assert metrics["error_rate"] == 12.7
    assert metrics["service"] == "web-api"


def test_http_missing_url_raises(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "http")
    monkeypatch.delenv("METRICS_URL", raising=False)
    with pytest.raises(adapter.UpstreamError, match="METRICS_URL"):
        adapter.get_metrics(None, None)


def test_files_rollback_writes_audit_not_fake_health(tmp_path: Path, monkeypatch):
    _write_company(tmp_path)
    monkeypatch.setenv("DATA_SOURCE", "files")
    monkeypatch.setenv("COMPANY_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ROLLBACK_WEBHOOK_URL", raising=False)
    result = adapter.execute_rollback("default", "inc_test")
    assert result["ok"] is True
    events = json.loads((tmp_path / "rollback_events.json").read_text(encoding="utf-8"))
    assert events[-1]["to"] == "v9.2.0"
    assert events[-1]["from"] == "v9.2.1"
    releases = json.loads((tmp_path / "releases.json").read_text(encoding="utf-8"))
    assert releases["desired_version"] == "v9.2.0"
    metrics = adapter.get_metrics(None, None)
    assert metrics["error_rate"] == 12.7


def test_http_execute_without_webhook_escalates(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "http")
    monkeypatch.setenv("RELEASES_URL", "http://127.0.0.1:9/releases")
    monkeypatch.delenv("ROLLBACK_WEBHOOK_URL", raising=False)

    def fake_release(_scenario=None):
        return {
            "version": "v2",
            "previous": "v1",
            "rollback_available": True,
            "missing": False,
        }

    monkeypatch.setattr(adapter, "get_latest_release", fake_release)
    result = adapter.execute_rollback("default", "inc_x")
    assert result["ok"] is False
    assert NO_ROLLBACK_ENDPOINT in result["message"]


def test_api_files_metrics_and_unauthorized_rollback(tmp_path: Path, monkeypatch):
    _write_company(tmp_path)
    monkeypatch.setenv("DATA_SOURCE", "files")
    monkeypatch.setenv("COMPANY_DATA_DIR", str(tmp_path))
    from backend.main import app

    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["status"] == "ok"
        assert health["data_mode"] == "company_files"
        metrics = client.get("/api/metrics").json()
        assert metrics["error_rate"] == 12.7
        inv = client.post(
            "/investigate",
            json={
                "prompt": "checkout-api is throwing 500 after the latest deploy",
                "scenario_id": "tc01_checkout_after_deploy",
            },
        )
        assert inv.status_code == 200, inv.text
        assert inv.json()["decision"]["observed_metrics"]["error_rate"] == 12.7
        incident_id = inv.json()["id"]
        missing = client.post(
            f"/incidents/{incident_id}/rollback",
            json={"authorized": True},
        )
        assert missing.status_code == 401
        rb = client.post(
            f"/incidents/{incident_id}/rollback",
            json={"authorized": True},
            headers={"Authorization": "Bearer replace_me_with_a_local_token"},
        )
        assert rb.status_code == 200, rb.text
        assert rb.json()["verification"]["metrics"]["error_rate"] == 12.7
        assert rb.json()["verification"]["recovered"] is False


def test_sample_bundle_execute_is_409(monkeypatch):
    monkeypatch.setenv("DATA_SOURCE", "files")
    monkeypatch.setenv("COMPANY_DATA_DIR", str(Path("does-not-exist-company-data")))
    from backend.main import app
    from backend.memory import store as memory

    decision = Decision(
        service="checkout-api",
        observed_metrics={"error_rate": 12.7, "latency_ms": 890, "status": "degraded"},
        evidence=["a", "b", "c"],
        recommendation=Recommendation.ROLLBACK,
        reason="test",
        confidence=0.9,
    )
    memory.init()
    memory.save_incident(
        "inc_sample_rb",
        {
            "id": "inc_sample_rb",
            "prompt": "x",
            "scenario_id": "default",
            "service": "web-api",
            "status": "recommended",
            "decision": decision.model_dump(),
            "verification": {},
            "traces": [],
            "release": {},
            "logs": [],
        },
    )
    memory.save_recommendation("inc_sample_rb", decision.model_dump())
    with TestClient(app) as client:
        rb = client.post(
            "/incidents/inc_sample_rb/rollback",
            json={"authorized": True},
            headers={"Authorization": "Bearer replace_me_with_a_local_token"},
        )
        assert rb.status_code == 409
        assert NO_ROLLBACK_ENDPOINT in rb.json()["detail"]
