#!/usr/bin/env python3
"""Demo path: investigate checkout 500 after deploy → ROLLBACK → authorized execute → healthy.

Uses DATA_SOURCE=sim (test store). Live company-file investigate is a separate path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATA_SOURCE", "sim")
os.environ.setdefault("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
os.environ.setdefault("DEVOPSPILOT_FORCE_HEURISTIC", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app
from backend.tools import sim_store
from fastapi.testclient import TestClient


def main() -> None:
    sim_store.reset_all()
    client = TestClient(app)
    inv = client.post(
        "/investigate",
        json={
            "prompt": "checkout-api is throwing 500 after the latest deploy",
            "scenario_id": "tc01_checkout_after_deploy",
        },
    )
    if inv.status_code != 200:
        print("investigate failed:", inv.status_code, inv.text)
        raise SystemExit(1)
    body = inv.json()
    print("recommendation:", body["decision"]["recommendation"])
    print("confidence:", body["decision"]["confidence"])
    print("evidence:")
    for e in body["decision"]["evidence"]:
        print(" -", e)
    rb = client.post(
        f"/incidents/{body['id']}/rollback",
        json={"authorized": True, "scenario_id": "tc01_checkout_after_deploy"},
        headers={"Authorization": "Bearer replace_me_with_a_local_token"},
    )
    rb.raise_for_status()
    metrics = rb.json()["verification"]["metrics"]
    print("after rollback:", metrics)
    if metrics["error_rate"] != 1.1 or metrics["latency_ms"] != 210:
        raise SystemExit("verification failed")
    print("demo ok")


if __name__ == "__main__":
    main()
