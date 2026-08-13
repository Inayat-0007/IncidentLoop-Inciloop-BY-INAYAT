from __future__ import annotations

from backend.policy.gate import evaluate_rollback_execution
from backend.schemas import Decision, Recommendation


def test_gate_requires_authorization():
    d = Decision(
        service="checkout-api",
        observed_metrics={"error_rate": 18.4},
        evidence=["a", "b", "c"],
        recommendation=Recommendation.ROLLBACK,
        reason="test",
        confidence=0.91,
    )
    ok, msg = evaluate_rollback_execution(
        authorized=False,
        token_ok=True,
        decision=d,
        scenario_id="tc01_checkout_after_deploy",
    )
    assert not ok
    assert "ESCALATE TO HUMAN" in msg
