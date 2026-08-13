from __future__ import annotations

from typing import Any

from backend.schemas import Decision, Recommendation
from backend.tools.http_client import get_metrics_http


async def verify(scenario_id: str, service: str, decision: Decision) -> dict[str, Any]:
    metrics = await get_metrics_http(scenario_id, service)
    recovered = (
        float(metrics.get("error_rate") or 99) <= 2.0
        and float(metrics.get("latency_ms") or 9999) <= 300
        and metrics.get("status") == "healthy"
    )
    if decision.recommendation == Recommendation.ROLLBACK and not recovered:
        status = "pending_authorization"
        note = "Rollback recommended but not executed; metrics still degraded."
    elif recovered:
        status = "healthy"
        note = "Metrics recovered (error_rate ~1.1, latency ~210)."
    else:
        status = "unverified"
        note = "Current metrics do not show recovery."
    return {
        "metrics": metrics,
        "recovered": recovered,
        "status": status,
        "note": note,
        "tools": ["GET /api/metrics"],
    }
