# Threat model — DevOpsPilot

## Assets

- Mock / file / HTTP telemetry used for recommendations (not a K8s control plane)
- Optional `ROLLBACK_WEBHOOK_URL` (CD hook; env only)
- LLM API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, Azure)
- Rollback bearer token (`ROLLBACK_TOKEN`)
- GitHub token (`GITHUB_TOKEN`) if `DATA_SOURCE=github`
- Incident memory (recommendations, traces)
- Knowledge corpus (runbooks)
- Company export files under `data/company/` (may contain operational data; do not commit PII)

## Actors

- Local demo user (trusted on loopback)
- Unauthenticated caller on the API port
- Agent graph (untrusted for *execution*; trusted for *recommendation*)
- MCP client (same tools; same policy)

## Trust boundaries

- Browser → FastAPI
- Graph nodes → tools (company files / operator HTTP URLs / GitHub / sim)
- Graph → LLM vendor (if keyed)
- Execute path → `ROLLBACK_WEBHOOK_URL` (if set)
- MCP stdio → same tools

## STRIDE (MVP)

| ID | Threat | Mitigation |
|---|---|---|
| T1 | Unauthorized rollback | Bearer `ROLLBACK_TOKEN` + body `authorized: true`; policy gate; negative tests |
| T2 | Agent auto-rollback | Tools used in investigate **do not** call rollback; execution is a separate route |
| T3 | Prompt injection → execute | Execution ignores LLM text for side effects; structured Decision + gate |
| T4 | Secret leak in logs/traces | Redact env keys; never log Authorization |
| T5 | SSRF via tools | `METRICS_URL` / `LOGS_URL` / `RELEASES_URL` / `ROLLBACK_WEBHOOK_URL` are **operator env only**, never taken from the prompt or query string |
| T6 | XSS in dashboard | React text nodes only; no `dangerouslySetInnerHTML` |
| T7 | Slopsquatting | `ALLOWED_DEPS.md` + `scripts/verify_allowed_deps.py` |
| T8 | Hallucinated rollback | Heuristic/LLM must fill Pydantic Decision; tests check evidence + enum |
| T9 | Fake recovery | Real modes must not rewrite metrics to 1.1%; missing webhook → 409 |

## Never do

- Execute rollback because the model said so in prose
- Skip auth on `POST /incidents/{id}/rollback` or `POST /api/releases/rollback`
- Commit `.env` or API keys
- Bind demo with `CORS *` plus credentials in a non-local profile
- Treat file `desired_version` or sim health as a live cluster mutate
- Take telemetry URLs from user prompts (SSRF)

## Abuse cases (tests)

- Missing bearer on rollback → 401
- Bearer without `authorized: true` → 403 ESCALATE TO HUMAN
- Rollback when decision was not ROLLBACK → 409
- Rollback when no target → 409 / ESCALATE
- HTTP/GitHub execute without `ROLLBACK_WEBHOOK_URL` → 409 `no real rollback endpoint configured`
- Sample-bundle execute without webhook → 409 (do not pretend production recovered)
