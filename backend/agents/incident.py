from __future__ import annotations

from typing import Any

from backend.llm import complete
from backend.tools.logs import get_logs
from backend.tools.monitoring import get_metrics


def investigate(scenario_id: str, service: str) -> dict[str, Any]:
    metrics = get_metrics(scenario_id, service)
    logs = get_logs(scenario_id, service)
    summary = (
        f"Incident on {service}: error_rate={metrics.get('error_rate')} "
        f"latency_ms={metrics.get('latency_ms')} status={metrics.get('status')} "
        f"log_lines={len(logs.get('lines') or [])} missing={logs.get('missing')}"
    )
    llm_note = complete(
        "You are the Incident Agent. Summarize telemetry in one sentence. No rollback.",
        summary,
    )
    return {
        "metrics": metrics,
        "logs": logs,
        "summary": llm_note or summary,
        "tools": ["monitoring.get_metrics", "logs.get_logs"],
    }
