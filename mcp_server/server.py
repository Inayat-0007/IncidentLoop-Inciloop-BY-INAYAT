#!/usr/bin/env python3
"""MCP server wrapping the same mock production tools as FastAPI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.policy.gate import evaluate_mcp_rollback
from backend.tools.logs import get_logs
from backend.tools.monitoring import get_metrics
from backend.tools.release import get_latest_release, rollback_release
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("devopspilot")


@mcp.tool()
def monitoring_metrics(scenario_id: str = "default", service: str = "checkout-api") -> dict:
    """Read simulated service metrics (error_rate, latency_ms)."""
    return get_metrics(scenario_id, service)


@mcp.tool()
def logs_tail(scenario_id: str = "default", service: str = "checkout-api") -> dict:
    """Read simulated ERROR/INFO log lines."""
    return get_logs(scenario_id, service)


@mcp.tool()
def release_latest(scenario_id: str = "default") -> dict:
    """Read simulated latest release and rollback target."""
    return get_latest_release(scenario_id)


@mcp.tool()
def release_rollback(
    scenario_id: str = "default",
    authorized: bool = False,
    token: str = "",
    incident_id: str = "",
) -> dict:
    """Execute simulated rollback. Same policy as HTTP: token + authorized + evidence/release/target."""
    ok, message = evaluate_mcp_rollback(
        token=token,
        authorized=authorized,
        scenario_id=scenario_id,
        incident_id=incident_id or None,
    )
    if not ok:
        return {"ok": False, "message": message}
    return rollback_release(scenario_id)


if __name__ == "__main__":
    mcp.run()
