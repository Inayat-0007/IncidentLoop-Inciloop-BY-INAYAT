"""HTTP client for FastAPI telemetry adapters.

Agents call GET /api/metrics, /api/logs, /api/releases/latest over HTTP
(ASGI, same process). Those routes read DATA_SOURCE (company files, HTTP
JSON, GitHub releases, or sim for tests) — not Datadog or Kubernetes.

Nested TCP to 127.0.0.1:8000 from inside the same uvicorn worker would
deadlock; ASGITransport avoids that while still exercising the routes.
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.config import TOOL_TIMEOUT_S
from backend.errors import GraphRunError

_app: Any = None


def bind_app(app: Any) -> None:
    global _app
    _app = app


class ToolHttpError(GraphRunError):
    def __init__(self, detail: str) -> None:
        super().__init__(502, "tool_upstream", detail)


async def fetch_json(path: str, params: dict[str, str | None] | None = None) -> dict[str, Any]:
    if _app is None:
        raise ToolHttpError("Internal HTTP app is not bound")
    query = {k: v for k, v in (params or {}).items() if v is not None}
    timeout = httpx.Timeout(TOOL_TIMEOUT_S)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://devopspilot.internal",
            timeout=timeout,
        ) as client:
            response = await client.get(path, params=query)
            response.raise_for_status()
            data = response.json()
    except ToolHttpError:
        raise
    except httpx.TimeoutException as exc:
        raise ToolHttpError(f"Timeout calling production tools {path}") from exc
    except httpx.HTTPStatusError as exc:
        raise ToolHttpError(
            f"Production tools {path} returned HTTP {exc.response.status_code}"
        ) from exc
    except Exception as exc:
        raise ToolHttpError(
            f"Production tools {path} failed ({type(exc).__name__})"
        ) from exc
    if not isinstance(data, dict):
        raise ToolHttpError(f"Production tools {path} returned non-object JSON")
    return data


async def get_metrics_http(scenario_id: str | None, service: str | None) -> dict[str, Any]:
    return await fetch_json(
        "/api/metrics",
        {"scenario_id": scenario_id, "service": service},
    )


async def get_logs_http(scenario_id: str | None, service: str | None) -> dict[str, Any]:
    return await fetch_json(
        "/api/logs",
        {"scenario_id": scenario_id, "service": service},
    )


async def get_latest_release_http(scenario_id: str | None) -> dict[str, Any]:
    return await fetch_json("/api/releases/latest", {"scenario_id": scenario_id})
