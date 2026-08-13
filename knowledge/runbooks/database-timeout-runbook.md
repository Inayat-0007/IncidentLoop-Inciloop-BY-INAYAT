# Database timeout runbook

Applies to checkout-primary and payment-primary Postgres.

## Symptoms

- `ERROR DB connection refused`
- `ERROR database timeout`
- Connection pool exhaustion after a release that changes query plans

## Actions

1. Confirm whether the database itself is down (platform) vs the new app build (bad queries).
2. If the timeout started immediately after `checkout-api` deploy and checkout is 500ing, this is a **release-coupled** failure.
3. Combined with the deployment rollback policy: **rollback-if-checkout-500-after-deploy-and-db-failures**.

Do not drop tables. Do not run unreviewed SQL. Escalate if the database is the only failing component and the app release is unchanged.
