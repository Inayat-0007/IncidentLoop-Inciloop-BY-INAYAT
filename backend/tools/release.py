from __future__ import annotations

from typing import Any

from backend.tools import sim_store


def get_latest_release(scenario_id: str | None = None) -> dict[str, Any]:
    snap = sim_store.get_scenario(scenario_id)
    release = snap.get("release")
    if release is None:
        return {
            "service": snap.get("service"),
            "version": None,
            "previous": None,
            "rollback_available": False,
            "missing": True,
            "scenario_id": scenario_id or "default",
        }
    return {
        "service": snap.get("service"),
        **release,
        "missing": False,
        "scenario_id": scenario_id or "default",
    }


def rollback_release(scenario_id: str | None = None) -> dict[str, Any]:
    """Mutate mock production. Callers MUST pass the policy gate first."""
    return sim_store.apply_rollback(scenario_id)
