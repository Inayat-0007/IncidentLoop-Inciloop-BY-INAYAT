from __future__ import annotations

from typing import Any

from backend.tools import sim_store

# In-process snapshot for GET /api/logs. Simulated production adapter, not a log vendor.


def get_logs(scenario_id: str | None = None, service: str | None = None) -> dict[str, Any]:
    snap = sim_store.get_scenario(scenario_id)
    svc = service or snap.get("service") or "checkout-api"
    missing = bool(snap.get("logs_missing"))
    lines = [] if missing else list(snap.get("logs") or [])
    return {
        "service": svc,
        "lines": lines,
        "missing": missing,
        "scenario_id": scenario_id or "default",
    }
