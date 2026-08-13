from __future__ import annotations

from typing import Any

from backend.tools.adapter import execute_rollback
from backend.tools.adapter import get_latest_release as _get_latest_release


def get_latest_release(scenario_id: str | None = None) -> dict[str, Any]:
    return _get_latest_release(scenario_id)


def rollback_release(scenario_id: str | None = None, incident_id: str | None = None) -> dict[str, Any]:
    """Callers MUST pass the policy gate first. Does not auto-rollback production."""
    return execute_rollback(scenario_id, incident_id)
