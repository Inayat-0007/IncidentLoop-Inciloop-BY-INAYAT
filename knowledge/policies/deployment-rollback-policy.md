# Deployment rollback policy

## Hard rule

Recommendation and execution are separate. Agents may **recommend** ROLLBACK. Humans (or a caller with `ROLLBACK_TOKEN` and `authorized: true`) execute it.

## Rollback-if-checkout-500-after-deploy-and-db-failures

Recommend ROLLBACK when **all** of the following hold:

1. Service is `checkout-api`.
2. Latest release `version` differs from `previous` (a real deploy happened).
3. Observed error_rate is high (typically ≥ 10%) and checkout requests fail with HTTP 500.
4. Logs show database failures (timeout or connection refused) and/or PaymentService timeouts that began with the deploy.
5. A rollback target exists (`previous` is set and `rollback_available` is true).

If (5) fails → **ESCALATE TO HUMAN** (do not invent a target).

If logs are missing → **ESCALATE**.

If the failing service is unknown → **reject / ESCALATE**.

If the system is healthy → **NO_ACTION**.

If errors are unrelated (inventory batch jobs, other services) → **INVESTIGATE**, do not roll back checkout-api.
