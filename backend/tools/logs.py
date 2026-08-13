from __future__ import annotations

from typing import Any

from backend.tools.adapter import get_logs as _get_logs


def get_logs(scenario_id: str | None = None, service: str | None = None) -> dict[str, Any]:
    return _get_logs(scenario_id, service)
