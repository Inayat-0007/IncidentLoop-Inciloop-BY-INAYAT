# Security

- Secrets from `.env` only. Names in `.env.example`.
- `ROLLBACK_TOKEN` required for mutations.
- Do not log tokens, API keys, or Authorization headers.
- LLM keys required for live investigate (`GEMINI_API_KEY`). Heuristic is test-only (`DEVOPSPILOT_FORCE_HEURISTIC`).
- Bind default demo to localhost in README.
