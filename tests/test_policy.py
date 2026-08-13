from __future__ import annotations

from backend.policy.gate import evaluate_mcp_rollback, evaluate_rollback_execution
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


def test_mcp_gate_refuses_unauthorized():
    d_ok, msg = evaluate_mcp_rollback(
        token="replace_me_with_a_local_token",
        authorized=False,
        scenario_id="tc01_checkout_after_deploy",
    )
    assert not d_ok
    assert "ESCALATE TO HUMAN" in msg


def test_mcp_gate_refuses_invalid_token():
    d_ok, msg = evaluate_mcp_rollback(
        token="wrong",
        authorized=True,
        scenario_id="tc01_checkout_after_deploy",
    )
    assert not d_ok
    assert "token" in msg.lower() or "ESCALATE TO HUMAN" in msg
