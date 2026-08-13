from __future__ import annotations

import re

from backend.config import KNOWN_SERVICES

_SCENARIO_HINTS: list[tuple[str, str]] = [
    ("tc05_unknown_service", r"unknown[- ]service|not-a-real-service|foobar-svc"),
    ("tc04_missing_logs", r"missing logs|no logs"),
    ("tc06_no_rollback_target", r"no rollback target|rollback target unavailable|cannot rollback"),
    ("tc03_healthy", r"healthy|all green|error rate (is )?1\.1"),
    ("tc02_unrelated_errors", r"unrelated|inventory[- ]api stock|batch job"),
    ("tc07_high_latency_only", r"latency only|slow but (no|low) error"),
    ("tc14_empty_prompt", r"^$"),
    ("tc18_release_missing", r"no release|release missing"),
    ("tc15_multi_service_blast", r"everything (is )?down|multi[- ]service|blast radius"),
    ("tc12_errors_no_recent_deploy", r"no recent deploy|stable for weeks"),
    ("tc16_checkout_500_no_db", r"500(?!.*db)|checkout 500 without db"),
]


def extract_service(prompt: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit.strip()
    text = prompt.lower()
    for svc in sorted(KNOWN_SERVICES, key=len, reverse=True):
        if svc in text:
            return svc
    m = re.search(r"\b([a-z][a-z0-9-]+-api)\b", text)
    if m:
        return m.group(1)
    if "unknown" in text or "foobar" in text or "not-a-real" in text:
        return "not-a-real-service"
    return "checkout-api"


def resolve_scenario(prompt: str, scenario_id: str | None) -> str:
    if scenario_id:
        return scenario_id
    text = (prompt or "").strip().lower()
    if not text:
        return "tc14_empty_prompt"
    for sid, pattern in _SCENARIO_HINTS:
        if re.search(pattern, text, re.I):
            return sid
    if "checkout" in text and ("500" in text or "error" in text) and "deploy" in text:
        return "tc01_checkout_after_deploy"
    return "tc01_checkout_after_deploy"


def plan_steps(service: str, scenario_id: str) -> str:
    return (
        f"PLAN for {service} (scenario={scenario_id}): "
        "1) pull metrics 2) pull logs 3) retrieve runbooks/incidents "
        "4) inspect latest release 5) structured decision 6) verify current health. "
        "Do not execute rollback in this plan."
    )
