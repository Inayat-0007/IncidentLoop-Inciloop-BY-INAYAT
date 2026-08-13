from __future__ import annotations

from typing import Any

from backend.tools import sim_store

# In-process snapshot for GET /api/metrics. Interview "simulated production"
# adapter — not Datadog, Prometheus, or Kubernetes. Agents call this route over HTTP.


def get_metrics(scenario_id: str | None = None, service: str | None = None) -> dict[str, Any]:
    snap = sim_store.get_scenario(scenario_id)
    svc = service or snap.get("service") or "checkout-api"
    metrics = dict(snap.get("metrics") or {})
    return {
        "service": svc,
        "error_rate": metrics.get("error_rate"),
        "latency_ms": metrics.get("latency_ms"),
        "status": metrics.get("status"),
        "scenario_id": scenario_id or "default",
    }
