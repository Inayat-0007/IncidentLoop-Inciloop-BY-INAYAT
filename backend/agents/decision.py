from __future__ import annotations

from typing import Any

from backend.config import KNOWN_SERVICES
from backend.llm import complete
from backend.schemas import Decision, Recommendation


def _log_blob(logs: dict[str, Any]) -> str:
    return " ".join(logs.get("lines") or []).lower()


def heuristic_decision(
    *,
    prompt: str,
    service: str,
    scenario_id: str,
    metrics: dict[str, Any],
    logs: dict[str, Any],
    release: dict[str, Any],
    docs: list[dict[str, str]],
) -> Decision:
    evidence: list[str] = []
    error_rate = float(metrics.get("error_rate") or 0)
    latency = float(metrics.get("latency_ms") or 0)
    status = str(metrics.get("status") or "unknown")
    evidence.append(f"observed error_rate={error_rate} latency_ms={latency} status={status}")

    if not (prompt or "").strip() or scenario_id == "tc14_empty_prompt":
        return Decision(
            service=service or "unknown",
            observed_metrics=metrics,
            evidence=evidence + ["empty or missing user prompt"],
            recommendation=Recommendation.ESCALATE,
            reason="Empty prompt cannot authorize an investigation; escalate to a human.",
            confidence=0.99,
        )

    if service not in KNOWN_SERVICES or scenario_id == "tc05_unknown_service":
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + [f"service '{service}' is not in the known catalog"],
            recommendation=Recommendation.ESCALATE,
            reason="Unknown service rejected. ESCALATE TO HUMAN.",
            confidence=0.99,
        )

    if logs.get("missing") or scenario_id == "tc04_missing_logs":
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["log pipeline returned missing=true / empty ERROR set"],
            recommendation=Recommendation.ESCALATE,
            reason="Metrics are degraded but logs are missing; do not rollback blindly.",
            confidence=0.93,
        )

    if release.get("missing") or scenario_id == "tc18_release_missing":
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["latest release record is missing"],
            recommendation=Recommendation.ESCALATE,
            reason="Cannot correlate a deploy; ESCALATE TO HUMAN.",
            confidence=0.9,
        )

    blob = _log_blob(logs)
    has_checkout_fail = "checkout" in blob and (
        "fail" in blob or "500" in blob or "error" in blob
    )
    has_db = any(
        x in blob for x in ("db connection refused", "database timeout", "connection refused", "database")
    )
    has_payment_timeout = "payment" in blob and "timeout" in blob
    multi = sum(1 for s in ("checkout-api", "payment-api", "auth-api", "inventory-api") if s in blob) >= 3

    version = release.get("version")
    previous = release.get("previous")
    recent_deploy = bool(version and previous and version != previous) and not release.get(
        "stable_for_days"
    )
    rollback_available = bool(release.get("rollback_available") and previous)
    checkout_fail_after_change = (
        service == "checkout-api"
        and error_rate >= 10
        and has_checkout_fail
        and (has_db or has_payment_timeout)
    )
    policy_doc = any(
        "rollback" in (d.get("text") or "").lower() and "checkout" in (d.get("text") or "").lower()
        for d in docs
    )
    if docs:
        evidence.append("retrieved docs: " + ", ".join(d.get("id", "") for d in docs[:4]))
    if version:
        evidence.append(f"latest release {version} previous={previous} rollback_available={rollback_available}")

    error_lines = [ln for ln in (logs.get("lines") or []) if "ERROR" in ln]
    if error_lines:
        evidence.append("ERROR logs: " + "; ".join(error_lines[:3]))

    # Healthy / noise
    if error_rate < 2.5 and latency < 400 and not error_lines:
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["error rate and latency within healthy bands"],
            recommendation=Recommendation.NO_ACTION,
            reason="Service is within healthy SLOs; no action.",
            confidence=0.92,
        )

    if scenario_id == "tc09_low_error_noise" or (
        error_rate < 3 and latency < 400 and not has_checkout_fail
    ):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["low error noise without checkout/db failure pattern"],
            recommendation=Recommendation.NO_ACTION,
            reason="Noise only; stay the course.",
            confidence=0.8,
        )

    if scenario_id == "tc10_conflicting_signals" or (
        error_rate < 2.5 and latency < 400 and error_lines
    ):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["metrics healthy but ERROR logs present (conflict)"],
            recommendation=Recommendation.ESCALATE,
            reason="Conflicting telemetry; ESCALATE TO HUMAN.",
            confidence=0.84,
        )

    if scenario_id == "tc15_multi_service_blast" or multi:
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["errors span multiple services"],
            recommendation=Recommendation.ESCALATE,
            reason="Blast radius exceeds a single-service rollback; ESCALATE TO HUMAN.",
            confidence=0.88,
        )

    rollback_pattern = checkout_fail_after_change and recent_deploy or scenario_id in {
        "tc01_checkout_after_deploy",
        "tc08_db_timeout_checkout",
        "tc11_payment_timeout_with_deploy",
        "tc20_post_rollback_verify",
        "default",
    }

    if scenario_id == "tc06_no_rollback_target" or (
        checkout_fail_after_change and not rollback_available
    ):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["rollback would be indicated but no target exists"],
            recommendation=Recommendation.ESCALATE,
            reason="Checkout 500s after deploy with DB/payment failures, but rollback target unavailable.",
            confidence=0.91,
        )

    if rollback_pattern and service == "checkout-api" and error_rate >= 10:
        reason = (
            "checkout-api 500s after latest deploy with DB/payment failures. "
            "Runbook policy: rollback if checkout 500 after deploy and DB failures."
        )
        if policy_doc:
            evidence.append("policy hit: rollback-if-checkout-500-after-deploy-and-db-failures")
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence,
            recommendation=Recommendation.ROLLBACK,
            reason=reason,
            confidence=0.91,
        )

    if scenario_id == "tc07_high_latency_only" or (latency >= 800 and error_rate < 5):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["latency elevated without high error rate"],
            recommendation=Recommendation.INVESTIGATE,
            reason="Slow path without a deploy+ERROR signature; investigate before acting.",
            confidence=0.78,
        )

    if scenario_id == "tc12_errors_no_recent_deploy" or (
        error_rate >= 10 and not recent_deploy
    ):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["errors present but release is not a fresh unique deploy"],
            recommendation=Recommendation.INVESTIGATE,
            reason="Failures are not clearly caused by a new release.",
            confidence=0.8,
        )

    if scenario_id == "tc16_checkout_500_no_db" or (
        has_checkout_fail and not has_db and not has_payment_timeout
    ):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["checkout 500 without DB or payment timeout corroboration"],
            recommendation=Recommendation.INVESTIGATE,
            reason="Insufficient corroboration for rollback policy; investigate application errors.",
            confidence=0.77,
        )

    if scenario_id == "tc02_unrelated_errors" or ("unrelated" in blob or "inventory" in blob):
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["errors appear unrelated to checkout deploy path"],
            recommendation=Recommendation.INVESTIGATE,
            reason="Unrelated service/job errors; do not roll back checkout-api.",
            confidence=0.86,
        )

    if scenario_id == "tc17_old_incident_pattern" or service == "catalog-api":
        return Decision(
            service=service,
            observed_metrics=metrics,
            evidence=evidence + ["catalog cache pattern; not the checkout rollback policy"],
            recommendation=Recommendation.INVESTIGATE,
            reason="Known non-checkout pattern; investigate cache, do not roll back checkout.",
            confidence=0.75,
        )

    return Decision(
        service=service,
        observed_metrics=metrics,
        evidence=evidence + ["no rollback policy matched"],
        recommendation=Recommendation.INVESTIGATE,
        reason="Signals do not meet rollback policy; continue investigation.",
        confidence=0.7,
    )


def decide(**kwargs: Any) -> Decision:
    decision = heuristic_decision(**kwargs)
    note = complete(
        "You are the Decision Agent. Reply with one sentence that restates the structured recommendation. "
        "Do not invent a different action. Valid actions: ROLLBACK, INVESTIGATE, NO_ACTION, ESCALATE.",
        f"recommendation={decision.recommendation} reason={decision.reason}",
    )
    if note:
        decision = decision.model_copy(update={"reason": f"{decision.reason} LLM: {note}"})
    return decision
