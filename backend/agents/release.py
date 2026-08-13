from __future__ import annotations

from typing import Any

from backend.config import use_gemini_for
from backend.llm import acomplete
from backend.tools.http_client import get_latest_release_http


async def inspect_release(scenario_id: str) -> dict[str, Any]:
    release = await get_latest_release_http(scenario_id)
    blob = (
        f"version={release.get('version')} previous={release.get('previous')} "
        f"rollback_available={release.get('rollback_available')} missing={release.get('missing')}"
    )
    if use_gemini_for("release"):
        note = await acomplete(
            "You are the Release Agent. Summarize the latest release and whether a rollback "
            "target exists. Do not execute rollback. Do not invent versions.",
            blob,
        )
    else:
        note = blob
    return {"release": release, "summary": note, "tools": ["GET /api/releases/latest"]}
