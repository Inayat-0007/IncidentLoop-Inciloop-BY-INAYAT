# PRD — DevOpsPilot MVP

## Problem

On-call engineers lose time correlating metrics, logs, recent deploys, and runbooks. Auto-remediation without a human is unsafe. Teams need a **recommend-then-verify** assistant, not a cluster autopilot.

## Audience

One engineering org in a **simulated** production sandbox (interview / demo). Not a multi-tenant SaaS.

## Pitch

Multi-agent production incident and release assistant: **PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY**.

## In scope (MVP)

1. Mock production APIs: metrics, logs, latest release, rollback (mutates mock health).
2. LangGraph: Planner → Incident → Knowledge → Release → Decision → Verification.
3. RAG over `knowledge/` (runbooks + historical incidents).
4. Evidence-based Pydantic `Decision` (never free-text-only).
5. Memory: conversation, incidents, recommendations, resolved incidents.
6. Policy gate: no rollback execution without authorization + evidence + rollback target.
7. AgentOps traces + React dashboard.
8. REST: investigate, get incident, authorized rollback, get traces.
9. MCP server wrapping the same tools.
10. ~20 fixed pytest scenarios (deterministic without LLM).

## Out of scope

Kubernetes operators, real APM, public status, on-call scheduling, Slack/PagerDuty writes, auto-resolve without a human, giant enterprise IAM.

## Acceptance (demo path)

User prompt: checkout-api 500s after latest deploy → system recommends **ROLLBACK** with evidence → user authorizes rollback → verification shows metrics recovered (error_rate ~1.1, latency ~210).

## Honest disclaimer

All telemetry and releases are **simulated**. No live production is queried or changed.
