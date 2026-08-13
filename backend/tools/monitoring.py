from __future__ import annotations

from typing import Any

from backend.tools.adapter import get_metrics as _get_metrics


def get_metrics(scenario_id: str | None = None, service: str | None = None) -> dict[str, Any]:
    return _get_metrics(scenario_id, service)
