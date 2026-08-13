from __future__ import annotations

import copy
import threading
from typing import Any

_lock = threading.Lock()

HEALTHY_METRICS = {
    "error_rate": 1.1,
    "latency_ms": 210,
    "status": "healthy",
}

_DEFAULTS: dict[str, dict[str, Any]] = {
    "tc01_checkout_after_deploy": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 18.4,
            "latency_ms": 1240,
            "status": "degraded",
        },
        "logs": [
            "ERROR PaymentService timeout waiting for gateway",
            "ERROR DB connection refused on checkout-primary:5432",
            "ERROR checkout failed with HTTP 500 for cart_id=c-9921",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
            "deployed_at": "2026-08-13T12:00:00Z",
        },
    },
    "default": {},  # filled from tc01 below
    "tc02_unrelated_errors": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 3.2,
            "latency_ms": 280,
            "status": "degraded",
        },
        "logs": [
            "ERROR inventory-api stock sync failed for sku=WIDGET",
            "WARN unrelated batch job missed SLA",
            "INFO checkout-api 200 GET /health",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
            "deployed_at": "2026-08-10T12:00:00Z",
        },
    },
    "tc03_healthy": {
        "service": "checkout-api",
        "metrics": dict(HEALTHY_METRICS),
        "logs": [
            "INFO checkout-api 200 POST /checkout",
            "INFO PaymentService ok",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
            "deployed_at": "2026-08-01T12:00:00Z",
        },
    },
    "tc04_missing_logs": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 18.4,
            "latency_ms": 1240,
            "status": "degraded",
        },
        "logs": [],
        "logs_missing": True,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
            "deployed_at": "2026-08-13T12:00:00Z",
        },
    },
    "tc05_unknown_service": {
        "service": "not-a-real-service",
        "metrics": {
            "error_rate": 50.0,
            "latency_ms": 5000,
            "status": "unknown",
        },
        "logs": ["ERROR mystery service crashed"],
        "logs_missing": False,
        "release": {
            "version": None,
            "previous": None,
            "rollback_available": False,
        },
    },
    "tc06_no_rollback_target": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 18.4,
            "latency_ms": 1240,
            "status": "degraded",
        },
        "logs": [
            "ERROR PaymentService timeout",
            "ERROR DB connection refused",
            "ERROR checkout failed",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": None,
            "rollback_available": False,
            "deployed_at": "2026-08-13T12:00:00Z",
        },
    },
    "tc07_high_latency_only": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 1.4,
            "latency_ms": 1320,
            "status": "degraded",
        },
        "logs": [
            "WARN checkout-api slow query 1100ms",
            "INFO PaymentService ok",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc08_db_timeout_checkout": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 16.0,
            "latency_ms": 980,
            "status": "degraded",
        },
        "logs": [
            "ERROR database timeout on checkout-primary",
            "ERROR checkout failed HTTP 500",
            "ERROR DB connection refused",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc09_low_error_noise": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 2.1,
            "latency_ms": 240,
            "status": "healthy",
        },
        "logs": ["WARN client timeout from flaky mobile network"],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc10_conflicting_signals": {
        "service": "checkout-api",
        "metrics": dict(HEALTHY_METRICS),
        "logs": [
            "ERROR checkout failed",
            "ERROR DB connection refused",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc11_payment_timeout_with_deploy": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 14.2,
            "latency_ms": 890,
            "status": "degraded",
        },
        "logs": [
            "ERROR PaymentService timeout",
            "ERROR checkout failed",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc12_errors_no_recent_deploy": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 18.4,
            "latency_ms": 1240,
            "status": "degraded",
        },
        "logs": [
            "ERROR PaymentService timeout",
            "ERROR DB connection refused",
            "ERROR checkout failed",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.7.0",
            "previous": "v2.7.0",
            "rollback_available": True,
            "stable_for_days": 21,
        },
    },
    "tc13_already_healthy_after_fix": {
        "service": "checkout-api",
        "metrics": dict(HEALTHY_METRICS),
        "logs": ["INFO checkout recovered after rollback to v2.8.0"],
        "logs_missing": False,
        "release": {
            "version": "v2.8.0",
            "previous": "v2.8.1",
            "rollback_available": False,
        },
    },
    "tc14_empty_prompt": {
        "service": "checkout-api",
        "metrics": dict(HEALTHY_METRICS),
        "logs": [],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc15_multi_service_blast": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 22.0,
            "latency_ms": 2000,
            "status": "degraded",
        },
        "logs": [
            "ERROR checkout-api 500",
            "ERROR payment-api 500",
            "ERROR auth-api 500",
            "ERROR inventory-api 500",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc16_checkout_500_no_db": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 12.0,
            "latency_ms": 700,
            "status": "degraded",
        },
        "logs": [
            "ERROR checkout failed HTTP 500",
            "INFO PaymentService ok",
            "INFO DB ok",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
    "tc17_old_incident_pattern": {
        "service": "catalog-api",
        "metrics": {
            "error_rate": 4.0,
            "latency_ms": 400,
            "status": "degraded",
        },
        "logs": ["ERROR catalog cache miss storm"],
        "logs_missing": False,
        "release": {
            "version": "v1.4.2",
            "previous": "v1.4.1",
            "rollback_available": True,
        },
    },
    "tc18_release_missing": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 18.4,
            "latency_ms": 1240,
            "status": "degraded",
        },
        "logs": [
            "ERROR PaymentService timeout",
            "ERROR DB connection refused",
            "ERROR checkout failed",
        ],
        "logs_missing": False,
        "release": None,
    },
    "tc20_post_rollback_verify": {
        "service": "checkout-api",
        "metrics": {
            "error_rate": 18.4,
            "latency_ms": 1240,
            "status": "degraded",
        },
        "logs": [
            "ERROR PaymentService timeout",
            "ERROR DB connection refused",
            "ERROR checkout failed",
        ],
        "logs_missing": False,
        "release": {
            "version": "v2.8.1",
            "previous": "v2.8.0",
            "rollback_available": True,
        },
    },
}

_DEFAULTS["default"] = copy.deepcopy(_DEFAULTS["tc01_checkout_after_deploy"])

_state: dict[str, dict[str, Any]] = {}


def reset_all() -> None:
    with _lock:
        _state.clear()
        for key, val in _DEFAULTS.items():
            _state[key] = copy.deepcopy(val)


reset_all()


def list_scenario_ids() -> list[str]:
    return sorted(_DEFAULTS.keys())


def get_scenario(scenario_id: str | None) -> dict[str, Any]:
    sid = scenario_id or "default"
    with _lock:
        if sid not in _state:
            _state[sid] = copy.deepcopy(_DEFAULTS.get("default", {}))
        return copy.deepcopy(_state[sid])


def apply_rollback(scenario_id: str | None) -> dict[str, Any]:
    sid = scenario_id or "default"
    with _lock:
        if sid not in _state:
            _state[sid] = copy.deepcopy(_DEFAULTS.get("default", {}))
        current = _state[sid]
        release = current.get("release") or {}
        previous = release.get("previous")
        current["metrics"] = dict(HEALTHY_METRICS)
        current["logs"] = [
            "INFO rollback complete",
            "INFO checkout-api recovered",
        ]
        current["logs_missing"] = False
        if release:
            current["release"] = {
                **release,
                "version": previous or release.get("version"),
                "previous": release.get("version"),
                "rollback_available": False,
                "rolled_back": True,
            }
        return copy.deepcopy(current)
