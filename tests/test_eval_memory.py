from __future__ import annotations

import os
import time

os.environ.setdefault("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
os.environ["DEVOPSPILOT_FORCE_HEURISTIC"] = "1"

from backend.evaluation.score import latency_wildly_broken, score_case, score_results
from backend.evaluation.test_cases import CASES
from backend.main import app
from backend.memory import store as memory
from backend.tools import sim_store
from fastapi.testclient import TestClient


def test_memory_recall_after_resolve():
    sim_store.reset_all()
    memory.reset()
    with TestClient(app) as client:
        inv = client.post(
            "/investigate",
            json={
                "prompt": (
                    "checkout-api is throwing 500 after the latest deploy, "
                    "payments timeout and DB connection refused"
                ),
                "scenario_id": "tc01_checkout_after_deploy",
            },
        )
        assert inv.status_code == 200
        incident_id = inv.json()["id"]
        rb = client.post(
            f"/incidents/{incident_id}/rollback",
            json={"authorized": True, "scenario_id": "tc01_checkout_after_deploy"},
            headers={"Authorization": "Bearer replace_me_with_a_local_token"},
        )
        assert rb.status_code == 200, rb.text
        again = client.post(
            "/investigate",
            json={
                "prompt": (
                    "did we see this before? checkout-api 500 after latest "
                    "deploy database timeout"
                ),
                "scenario_id": "tc01_checkout_after_deploy",
            },
        )
        assert again.status_code == 200, again.text
        body = again.json()
        blob = (
            " ".join(body["decision"]["evidence"])
            + " "
            + " ".join(
                d
                for t in body.get("traces") or []
                for d in (t.get("docs_retrieved") or [])
            )
        )
        assert incident_id in blob
        assert "memory" in blob.lower() or incident_id in blob
    sim_store.reset_all()
    memory.reset()


def test_heuristic_eval_scores_100():
    sim_store.reset_all()
    rows = []
    with TestClient(app) as client:
        for case in CASES:
            t0 = time.perf_counter()
            r = client.post(
                "/investigate",
                json={"prompt": case.prompt, "scenario_id": case.scenario_id},
            )
            latency_ms = (time.perf_counter() - t0) * 1000
            assert r.status_code == 200, r.text
            rows.append(score_case(case, r.json(), latency_ms))
    report = score_results(rows)
    print(report.as_text())
    assert report.decision_accuracy == 100.0
    assert report.tool_call_correctness == 100.0
    assert report.rag_relevance == 100.0
    assert not latency_wildly_broken(report)
    sim_store.reset_all()
