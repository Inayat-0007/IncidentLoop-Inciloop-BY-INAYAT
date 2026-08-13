from __future__ import annotations

from backend.config import ROLLBACK_TOKEN
from backend.schemas import Decision, Recommendation
from backend.tools.release import get_latest_release


def token_matches(token: str | None) -> bool:
    if not token:
        return False
    return token.strip() == ROLLBACK_TOKEN


def evaluate_rollback_execution(
    *,
    authorized: bool,
    token_ok: bool,
    decision: Decision,
    scenario_id: str | None,
) -> tuple[bool, str]:
    """Return (allowed, message). Recommendation vs execution are separate."""
    if not token_ok:
        return False, "ESCALATE TO HUMAN: missing or invalid rollback token"
    if not authorized:
        return False, "ESCALATE TO HUMAN: rollback requires explicit user authorization"
    if decision.recommendation != Recommendation.ROLLBACK:
        return False, "ESCALATE TO HUMAN: execution refused because recommendation is not ROLLBACK"
    if decision.confidence < 0.7:
        return False, "ESCALATE TO HUMAN: confidence below evidence threshold"
    if len(decision.evidence) < 3:
        return False, "ESCALATE TO HUMAN: insufficient evidence bullets"
    release = get_latest_release(scenario_id)
    if release.get("missing") or not release.get("version"):
        return False, "ESCALATE TO HUMAN: no current release found"
    if not release.get("rollback_available") or not release.get("previous"):
        return False, "ESCALATE TO HUMAN: rollback target does not exist"
    return True, "policy_ok"


def evaluate_mcp_rollback(
    *,
    token: str | None,
    authorized: bool,
    scenario_id: str | None,
    incident_id: str | None = None,
) -> tuple[bool, str]:
    """Same execution gate as HTTP. Fail closed if no stored ROLLBACK recommendation."""
    from backend.memory import store as memory

    decision: Decision | None = None
    if incident_id:
        row = memory.get_incident(incident_id)
        if row and row.get("decision"):
            decision = Decision.model_validate(row["decision"])
    if decision is None:
        recs = memory.previous_recommendations(limit=1)
        if recs:
            try:
                decision = Decision.model_validate(recs[0])
            except Exception:
                decision = None
    if decision is None:
        decision = Decision(
            service="unknown",
            evidence=["no stored investigation"],
            recommendation=Recommendation.INVESTIGATE,
            reason="MCP rollback refused: no stored ROLLBACK recommendation",
            confidence=0.0,
        )
    return evaluate_rollback_execution(
        authorized=authorized,
        token_ok=token_matches(token),
        decision=decision,
        scenario_id=scenario_id,
    )
