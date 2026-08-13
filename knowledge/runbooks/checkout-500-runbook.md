# Checkout 500 runbook

Service: `checkout-api`

## Symptoms

- HTTP 500 on `POST /checkout`
- Elevated error_rate (>10%) and latency_ms (>800)
- `ERROR checkout failed` in application logs

## Immediate checks

1. Pull `GET /api/metrics` for checkout-api.
2. Pull `GET /api/logs` and look for PaymentService timeout and DB connection refused.
3. Pull `GET /api/releases/latest` — compare `version` vs `previous`.

## Policy

If checkout-api returns 500 after the latest deploy **and** there are database failures (timeout or connection refused), **recommend ROLLBACK** to the previous version. Do not execute rollback without a human authorization token.

If 500s occur without DB or payment corroboration, **INVESTIGATE** the application error instead of rolling back.
