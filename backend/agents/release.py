from __future__ import annotations

from typing import Any

from backend.tools.release import get_latest_release


def inspect_release(scenario_id: str) -> dict[str, Any]:
    release = get_latest_release(scenario_id)
    return {"release": release, "tools": ["release.get_latest_release"]}
