from __future__ import annotations

from dataclasses import dataclass

from backend.schemas import Recommendation


@dataclass(frozen=True)
class EvalCase:
    id: str
    scenario_id: str
    prompt: str
    expected: Recommendation


CASES: list[EvalCase] = [
    EvalCase(
        "TC01",
        "tc01_checkout_after_deploy",
        "checkout-api is throwing 500 after the latest deploy, payments timeout and DB connection refused",
        Recommendation.ROLLBACK,
    ),
    EvalCase(
        "TC02",
        "tc02_unrelated_errors",
        "unrelated inventory-api stock sync errors and a batch job missed SLA",
        Recommendation.INVESTIGATE,
    ),
    EvalCase(
        "TC03",
        "tc03_healthy",
        "checkout-api looks healthy, error rate is 1.1",
        Recommendation.NO_ACTION,
    ),
    EvalCase(
        "TC04",
        "tc04_missing_logs",
        "checkout-api degraded but missing logs from the pipeline",
        Recommendation.ESCALATE,
    ),
    EvalCase(
        "TC05",
        "tc05_unknown_service",
        "page not-a-real-service unknown service is on fire",
        Recommendation.ESCALATE,
    ),
    EvalCase(
        "TC06",
        "tc06_no_rollback_target",
        "checkout-api 500 after deploy but rollback target unavailable",
        Recommendation.ESCALATE,
    ),
    EvalCase(
        "TC07",
        "tc07_high_latency_only",
        "checkout-api latency only, slow but low errors",
        Recommendation.INVESTIGATE,
    ),
    EvalCase(
        "TC08",
        "tc08_db_timeout_checkout",
        "checkout-api 500 with database timeout after latest deploy",
        Recommendation.ROLLBACK,
    ),
    EvalCase(
        "TC09",
        "tc09_low_error_noise",
        "tiny error noise on checkout-api",
        Recommendation.NO_ACTION,
    ),
    EvalCase(
        "TC10",
        "tc10_conflicting_signals",
        "metrics healthy but ERROR logs on checkout-api",
        Recommendation.ESCALATE,
    ),
    EvalCase(
        "TC11",
        "tc11_payment_timeout_with_deploy",
        "checkout-api 500 after latest deploy PaymentService timeout",
        Recommendation.ROLLBACK,
    ),
    EvalCase(
        "TC12",
        "tc12_errors_no_recent_deploy",
        "checkout-api errors with no recent deploy, stable for weeks",
        Recommendation.INVESTIGATE,
    ),
    EvalCase(
        "TC13",
        "tc13_already_healthy_after_fix",
        "checkout-api already healthy after fix",
        Recommendation.NO_ACTION,
    ),
    EvalCase(
        "TC14",
        "tc14_empty_prompt",
        "",
        Recommendation.ESCALATE,
    ),
    EvalCase(
        "TC15",
        "tc15_multi_service_blast",
        "everything is down multi-service blast radius",
        Recommendation.ESCALATE,
    ),
    EvalCase(
        "TC16",
        "tc16_checkout_500_no_db",
        "checkout-api 500 after deploy without db failures",
        Recommendation.INVESTIGATE,
    ),
    EvalCase(
        "TC17",
        "tc17_old_incident_pattern",
        "catalog-api cache miss storm similar to last month",
        Recommendation.INVESTIGATE,
    ),
    EvalCase(
        "TC18",
        "tc18_release_missing",
        "checkout-api 500 after deploy but release missing from the catalog",
        Recommendation.ESCALATE,
    ),
]
