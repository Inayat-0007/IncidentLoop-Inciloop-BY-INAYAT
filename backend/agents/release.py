from __future__ import annotations

from typing import Any

from backend.tools.http_client import get_latest_release_http


async def inspect_release(scenario_id: str) -> dict[str, Any]:
    release = await get_latest_release_http(scenario_id)
    return {"release": release, "tools": ["GET /api/releases/latest"]}
