from __future__ import annotations

import asyncio
from typing import Any

from backend.config import use_gemini_for
from backend.llm import acomplete
from backend.tools.http_client import get_logs_http, get_metrics_http


async def investigate(scenario_id: str, service: str) -> dict[str, Any]:
    metrics, logs = await asyncio.gather(
        get_metrics_http(scenario_id, service),
        get_logs_http(scenario_id, service),
    )
    summary = (
        f"Incident on {service}: error_rate={metrics.get('error_rate')} "
        f"latency_ms={metrics.get('latency_ms')} status={metrics.get('status')} "
        f"log_lines={len(logs.get('lines') or [])} missing={logs.get('missing')}"
    )
    if use_gemini_for("incident"):
        note = await acomplete(
            "You are the Incident Agent. Summarize telemetry in one sentence. "
            "Do not recommend ROLLBACK. Do not invent metrics.",
            summary,
        )
    else:
        note = summary
    return {
        "metrics": metrics,
        "logs": logs,
        "summary": note,
        "tools": ["GET /api/metrics", "GET /api/logs"],
    }
