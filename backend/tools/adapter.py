"""Company data adapters: files (default live), HTTP JSON, GitHub releases, sim (tests).

Never invent metrics (no hardcoded 18.4 on the live path). Operator URLs come from
env only — not from the incident prompt. Rollback still requires the policy gate;
this module only mutates after callers have authorized.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from backend.config import (
    ROLLBACK_TOKEN,
    ROOT,
    TOOL_TIMEOUT_S,
    company_data_dir,
    data_source,
    github_repo,
    github_token,
    logs_url,
    metrics_url,
    releases_url,
    rollback_webhook_url,
)
from backend.tools import sim_store

NO_ROLLBACK_ENDPOINT = "no real rollback endpoint configured"

_BADGES = {
    "files": "Company files",
    "http": "HTTP tools",
    "github": "GitHub releases",
    "sim": "Sim (tests only)",
}


class UpstreamError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def describe_source() -> dict[str, str]:
    src = data_source()
    mode = _files_mode() if src == "files" else src
    return {
        "data_source": src,
        "data_mode": mode,
        "badge": _BADGES.get(src, src),
    }


def _files_mode() -> str:
    live = company_data_dir()
    if (live / "metrics.json").is_file():
        return "company_files"
    return "sample_bundle"


def _sample_dir() -> Path:
    return ROOT / "data" / "company" / "sample"


def _files_root() -> Path:
    if _files_mode() == "company_files":
        return company_data_dir()
    return _sample_dir()


def _annotate(payload: dict[str, Any]) -> dict[str, Any]:
    payload.update(describe_source())
    return payload


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _prom_value(series: dict[str, Any]) -> float | None:
    raw = series.get("value")
    if isinstance(raw, list) and len(raw) >= 2:
        try:
            return float(raw[1])
        except (TypeError, ValueError):
            return None
    values = series.get("values")
    if isinstance(values, list) and values:
        last = values[-1]
        if isinstance(last, list) and len(last) >= 2:
            try:
                return float(last[1])
            except (TypeError, ValueError):
                return None
    return None


def _maybe_percent(value: float, name: str) -> float:
    lowered = name.lower()
    if value <= 1.0 and any(k in lowered for k in ("error", "ratio", "rate", "5xx")):
        return round(value * 100.0, 4)
    return value


def _maybe_ms(value: float, name: str) -> float:
    lowered = name.lower()
    if value < 20 and any(k in lowered for k in ("latency", "duration", "seconds")):
        return round(value * 1000.0, 2)
    return value


def normalize_metrics(payload: Any, service: str | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise UpstreamError("metrics payload must be a JSON object")
    if "error_rate" in payload or "latency_ms" in payload or "status" in payload:
        svc = service or payload.get("service") or "unknown"
        status = payload.get("status")
        if status is None:
            try:
                status = "degraded" if float(payload.get("error_rate") or 0) >= 5 else "unknown"
            except (TypeError, ValueError):
                status = "unknown"
        return {
            "service": svc,
            "error_rate": payload.get("error_rate"),
            "latency_ms": payload.get("latency_ms"),
            "status": status,
        }
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("result"), list):
        error_rate = None
        latency_ms = None
        svc = service
        for series in data["result"]:
            if not isinstance(series, dict):
                continue
            metric = series.get("metric") if isinstance(series.get("metric"), dict) else {}
            name = str(metric.get("__name__") or "")
            if not svc:
                svc = metric.get("service") or metric.get("job")
            value = _prom_value(series)
            if value is None:
                continue
            lowered = name.lower()
            if error_rate is None and any(k in lowered for k in ("error", "5xx", "failed")):
                error_rate = _maybe_percent(value, name)
            if latency_ms is None and any(k in lowered for k in ("latency", "duration")):
                latency_ms = _maybe_ms(value, name)
        status = "unknown"
        try:
            if error_rate is not None:
                status = "degraded" if float(error_rate) >= 5 else "healthy"
        except (TypeError, ValueError):
            status = "unknown"
        return {
            "service": svc or "unknown",
            "error_rate": error_rate,
            "latency_ms": latency_ms,
            "status": status,
        }
    raise UpstreamError("metrics JSON did not match {service,error_rate,latency_ms} or Prometheus result")


def normalize_logs(payload: Any, service: str | None) -> dict[str, Any]:
    if payload is None:
        return {"service": service or "unknown", "lines": [], "missing": True}
    if isinstance(payload, list):
        lines = [_line_from_item(item) for item in payload]
        lines = [ln for ln in lines if ln]
        return {"service": service or "unknown", "lines": lines, "missing": not lines}
    if isinstance(payload, dict):
        svc = service or payload.get("service") or "unknown"
        raw_lines = payload.get("lines")
        if isinstance(raw_lines, list):
            lines = [_line_from_item(item) for item in raw_lines]
            lines = [ln for ln in lines if ln]
            missing = bool(payload.get("missing")) or not lines
            return {"service": svc, "lines": lines, "missing": missing}
        if "message" in payload or "line" in payload:
            line = _line_from_item(payload)
            return {"service": svc, "lines": [line] if line else [], "missing": not line}
    raise UpstreamError("logs JSON must be an array of strings or {lines:[]}")


def _line_from_item(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("line", "message", "msg", "text"):
            val = item.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def normalize_release(payload: Any, service: str | None) -> dict[str, Any]:
    if payload is None:
        return {
            "service": service,
            "version": None,
            "previous": None,
            "rollback_available": False,
            "missing": True,
        }
    if isinstance(payload, list):
        if not payload:
            return {
                "service": service,
                "version": None,
                "previous": None,
                "rollback_available": False,
                "missing": True,
            }
        payload = payload[0]
    if not isinstance(payload, dict):
        raise UpstreamError("releases payload must be a JSON object")
    version = payload.get("version") or payload.get("tag_name") or payload.get("name")
    previous = payload.get("previous") or payload.get("previous_version")
    rollback_available = payload.get("rollback_available")
    if rollback_available is None:
        rollback_available = bool(version and previous)
    missing = not version
    return {
        "service": service or payload.get("service"),
        "version": version,
        "previous": previous,
        "rollback_available": bool(rollback_available) and bool(previous),
        "deployed_at": payload.get("deployed_at") or payload.get("published_at"),
        "desired_version": payload.get("desired_version"),
        "missing": missing,
    }


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UpstreamError(f"missing company data file: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise UpstreamError(f"invalid JSON in {path.name}") from exc


def _read_logs_file(root: Path, service: str | None) -> dict[str, Any]:
    jsonl = root / "logs.jsonl"
    json_path = root / "logs.json"
    if jsonl.is_file():
        lines: list[str] = []
        for raw in jsonl.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            if raw.startswith("{") or raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    lines.append(raw)
                    continue
                if isinstance(parsed, list):
                    lines.extend(_line_from_item(x) for x in parsed)
                else:
                    line = _line_from_item(parsed)
                    lines.append(line or raw)
            else:
                lines.append(raw)
        lines = [ln for ln in lines if ln]
        return {"service": service or "unknown", "lines": lines, "missing": not lines}
    if json_path.is_file():
        return normalize_logs(_read_json_file(json_path), service)
    return {"service": service or "unknown", "lines": [], "missing": True}


def _http_get_json(url: str, label: str, headers: dict[str, str] | None = None) -> Any:
    timeout = httpx.Timeout(TOOL_TIMEOUT_S)
    try:
        response = httpx.get(url, headers=headers or {}, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException as exc:
        raise UpstreamError(f"Timeout fetching {label}") from exc
    except httpx.HTTPStatusError as exc:
        raise UpstreamError(f"{label} returned HTTP {exc.response.status_code}") from exc
    except Exception as exc:
        raise UpstreamError(f"{label} failed ({type(exc).__name__})") from exc


def _files_metrics(service: str | None) -> dict[str, Any]:
    root = _files_root()
    payload = _read_json_file(root / "metrics.json")
    return normalize_metrics(payload, service)


def _files_logs(service: str | None) -> dict[str, Any]:
    root = _files_root()
    parsed = _read_logs_file(root, service)
    if not parsed.get("service") or parsed["service"] == "unknown":
        try:
            parsed["service"] = _files_metrics(service).get("service") or parsed["service"]
        except UpstreamError:
            pass
    return parsed


def _files_release(service: str | None) -> dict[str, Any]:
    root = _files_root()
    path = root / "releases.json"
    if not path.is_file():
        return normalize_release(None, service)
    return normalize_release(_read_json_file(path), service)


def _http_metrics(service: str | None) -> dict[str, Any]:
    url = metrics_url()
    if not url:
        raise UpstreamError("METRICS_URL is not set")
    return normalize_metrics(_http_get_json(url, "METRICS_URL"), service)


def _http_logs(service: str | None) -> dict[str, Any]:
    url = logs_url()
    if not url:
        raise UpstreamError("LOGS_URL is not set")
    return normalize_logs(_http_get_json(url, "LOGS_URL"), service)


def _http_release(service: str | None) -> dict[str, Any]:
    url = releases_url()
    if not url:
        raise UpstreamError("RELEASES_URL is not set")
    return normalize_release(_http_get_json(url, "RELEASES_URL"), service)


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "DevOpsPilot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_release(service: str | None) -> dict[str, Any]:
    repo = github_repo()
    if not repo or "/" not in repo:
        raise UpstreamError("GITHUB_REPO must be owner/name")
    owner, name = repo.split("/", 1)
    base = f"https://api.github.com/repos/{owner}/{name}"
    releases = _http_get_json(f"{base}/releases", "GitHub releases", _github_headers())
    if isinstance(releases, list) and releases:
        latest = releases[0] if isinstance(releases[0], dict) else {}
        previous = None
        if len(releases) > 1 and isinstance(releases[1], dict):
            previous = releases[1].get("tag_name") or releases[1].get("name")
        return normalize_release(
            {
                "version": latest.get("tag_name") or latest.get("name"),
                "previous": previous,
                "previous_version": previous,
                "rollback_available": bool(previous),
                "published_at": latest.get("published_at"),
                "service": service,
            },
            service,
        )
    tags = _http_get_json(f"{base}/tags", "GitHub tags", _github_headers())
    if isinstance(tags, list) and tags:
        latest = tags[0] if isinstance(tags[0], dict) else {}
        previous = None
        if len(tags) > 1 and isinstance(tags[1], dict):
            previous = tags[1].get("name")
        return normalize_release(
            {
                "version": latest.get("name"),
                "previous": previous,
                "rollback_available": bool(previous),
                "service": service,
            },
            service,
        )
    return normalize_release(None, service)


def get_metrics(scenario_id: str | None = None, service: str | None = None) -> dict[str, Any]:
    src = data_source()
    if src == "sim":
        snap = sim_store.get_scenario(scenario_id)
        svc = service or snap.get("service") or "checkout-api"
        metrics = dict(snap.get("metrics") or {})
        return _annotate(
            {
                "service": svc,
                "error_rate": metrics.get("error_rate"),
                "latency_ms": metrics.get("latency_ms"),
                "status": metrics.get("status"),
                "scenario_id": scenario_id or "default",
            }
        )
    if src == "http":
        body = _http_metrics(service)
    else:
        body = _files_metrics(service)
        if service:
            body["service"] = service
    body["scenario_id"] = scenario_id or "default"
    return _annotate(body)


def get_logs(scenario_id: str | None = None, service: str | None = None) -> dict[str, Any]:
    src = data_source()
    if src == "sim":
        snap = sim_store.get_scenario(scenario_id)
        svc = service or snap.get("service") or "checkout-api"
        missing = bool(snap.get("logs_missing"))
        lines = [] if missing else list(snap.get("logs") or [])
        return _annotate(
            {
                "service": svc,
                "lines": lines,
                "missing": missing,
                "scenario_id": scenario_id or "default",
            }
        )
    if src == "http":
        body = _http_logs(service)
    else:
        body = _files_logs(service)
        if service:
            body["service"] = service
    body["scenario_id"] = scenario_id or "default"
    return _annotate(body)


def get_latest_release(scenario_id: str | None = None) -> dict[str, Any]:
    src = data_source()
    if src == "sim":
        snap = sim_store.get_scenario(scenario_id)
        release = snap.get("release")
        if release is None:
            return _annotate(
                {
                    "service": snap.get("service"),
                    "version": None,
                    "previous": None,
                    "rollback_available": False,
                    "missing": True,
                    "scenario_id": scenario_id or "default",
                }
            )
        return _annotate(
            {
                "service": snap.get("service"),
                **release,
                "missing": False,
                "scenario_id": scenario_id or "default",
            }
        )
    if src == "http":
        body = _http_release(None)
    elif src == "github":
        body = _github_release(None)
    else:
        body = _files_release(None)
    body["scenario_id"] = scenario_id or "default"
    return _annotate(body)


def _post_webhook(from_version: str | None, to_version: str | None, incident_id: str | None) -> dict[str, Any]:
    url = rollback_webhook_url()
    if not url:
        return {"ok": False, "skipped": True, "message": NO_ROLLBACK_ENDPOINT}
    timeout = httpx.Timeout(TOOL_TIMEOUT_S)
    try:
        response = httpx.post(
            url,
            json={"from": from_version, "to": to_version, "incident_id": incident_id},
            headers={"Authorization": f"Bearer {ROLLBACK_TOKEN}", "Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        body: Any
        try:
            body = response.json()
        except Exception:
            body = {"text": response.text[:500]}
        return {"ok": True, "status_code": response.status_code, "body": body}
    except httpx.TimeoutException as exc:
        raise UpstreamError("Timeout calling ROLLBACK_WEBHOOK_URL") from exc
    except httpx.HTTPStatusError as exc:
        raise UpstreamError(f"ROLLBACK_WEBHOOK_URL returned HTTP {exc.response.status_code}") from exc
    except UpstreamError:
        raise
    except Exception as exc:
        raise UpstreamError(f"ROLLBACK_WEBHOOK_URL failed ({type(exc).__name__})") from exc


def _append_rollback_event(event: dict[str, Any]) -> Path | None:
    live = company_data_dir()
    live.mkdir(parents=True, exist_ok=True)
    path = live / "rollback_events.json"
    rows: list[Any] = []
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                rows = loaded
        except json.JSONDecodeError:
            rows = []
    rows.append(event)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return path


def _flip_desired_version(to_version: str | None) -> bool:
    if not to_version:
        return False
    path = company_data_dir() / "releases.json"
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    payload["desired_version"] = to_version
    try:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        return False
    return True


def execute_rollback(scenario_id: str | None = None, incident_id: str | None = None) -> dict[str, Any]:
    """Mutate only after the policy gate. Sim recovers mock health; real modes do not invent 1.1%."""
    src = data_source()
    if src == "sim":
        snap = sim_store.apply_rollback(scenario_id)
        return {
            "ok": True,
            "executed": True,
            "message": "Simulated rollback applied (test/CI store only).",
            "release": snap.get("release"),
            "snapshot": snap,
            **describe_source(),
        }

    current = get_latest_release(scenario_id)
    from_version = current.get("version")
    to_version = current.get("previous")
    webhook_url = rollback_webhook_url()

    if webhook_url:
        webhook = _post_webhook(from_version, to_version, incident_id)
        audit = {
            "at": _iso_now(),
            "from": from_version,
            "to": to_version,
            "incident_id": incident_id,
            "via": "webhook",
        }
        if src == "files" and _files_mode() == "company_files":
            _append_rollback_event(audit)
            _flip_desired_version(to_version)
        return {
            "ok": True,
            "executed": True,
            "message": (
                "Rollback webhook accepted. Production health is whatever your CD reports — "
                "metrics were not invented."
            ),
            "release": current,
            "webhook": webhook,
            **describe_source(),
        }

    if src == "files":
        if _files_mode() != "company_files":
            return {
                "ok": False,
                "executed": False,
                "message": NO_ROLLBACK_ENDPOINT,
                "release": current,
                **describe_source(),
            }
        event = {
            "at": _iso_now(),
            "from": from_version,
            "to": to_version,
            "incident_id": incident_id,
            "via": "files_audit",
        }
        path = _append_rollback_event(event)
        flipped = _flip_desired_version(to_version)
        note = (
            "Recorded rollback intent in data/company/rollback_events.json. "
            "This is not Kubernetes. Metrics files were not rewritten to a fake healthy band."
        )
        if flipped:
            note += " Set desired_version in releases.json (local desired state only)."
        return {
            "ok": True,
            "executed": True,
            "message": note,
            "release": get_latest_release(scenario_id),
            "audit_path": str(path) if path else None,
            **describe_source(),
        }

    return {
        "ok": False,
        "executed": False,
        "message": NO_ROLLBACK_ENDPOINT,
        "release": current,
        **describe_source(),
    }


def recovered_from_metrics(metrics: dict[str, Any]) -> bool:
    try:
        error_rate = float(metrics.get("error_rate") or 99)
        latency = float(metrics.get("latency_ms") or 9999)
    except (TypeError, ValueError):
        return False
    return error_rate <= 2.0 and latency <= 300 and metrics.get("status") == "healthy"
