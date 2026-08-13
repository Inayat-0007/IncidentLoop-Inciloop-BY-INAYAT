# Threat model — DevOpsPilot

## Assets

- Mock production control plane (rollback mutates sim state)
- LLM API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, Azure)
- Rollback bearer token (`ROLLBACK_TOKEN`)
- Incident memory (recommendations, traces)
- Knowledge corpus (runbooks)

## Actors

- Local demo user (trusted on loopback)
- Unauthenticated caller on the API port
- Agent graph (untrusted for *execution*; trusted for *recommendation*)
- MCP client (same tools; same policy)

## Trust boundaries

- Browser → FastAPI
- Graph nodes → tools (in-process sim)
- Graph → LLM vendor (if keyed)
- MCP stdio → same tools

## STRIDE (MVP)

| ID | Threat | Mitigation |
|---|---|---|
| T1 | Unauthorized rollback | Bearer `ROLLBACK_TOKEN` + body `authorized: true`; policy gate; negative tests |
| T2 | Agent auto-rollback | Tools used in investigate **do not** call rollback; execution is a separate route |
| T3 | Prompt injection → execute | Execution ignores LLM text for side effects; structured Decision + gate |
| T4 | Secret leak in logs/traces | Redact env keys; never log Authorization |
| T5 | SSRF via tools | Tools only hit in-process sim, not arbitrary URLs |
| T6 | XSS in dashboard | React text nodes only; no `dangerouslySetInnerHTML` |
| T7 | Slopsquatting | `ALLOWED_DEPS.md` + `scripts/verify_allowed_deps.py` |
| T8 | Hallucinated rollback | Heuristic/LLM must fill Pydantic Decision; tests check evidence + enum |

## Never do

- Execute rollback because the model said so in prose
- Skip auth on `POST /incidents/{id}/rollback` or `POST /api/releases/rollback`
- Commit `.env` or API keys
- Bind demo with `CORS *` plus credentials in a non-local profile
- Treat mock APIs as real production

## Abuse cases (tests)

- Missing bearer on rollback → 401
- Bearer without `authorized: true` → 403 ESCALATE TO HUMAN
- Rollback when decision was not ROLLBACK → 409
- Rollback when no target → 409 / ESCALATE
