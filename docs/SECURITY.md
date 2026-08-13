# Security

- `DATA_SOURCE` selects files / http / github / sim (sim is tests only).
- `ROLLBACK_TOKEN` required for mutations.
- `ROLLBACK_WEBHOOK_URL` is optional; without it, real execute 409s except files audit.
- Do not log tokens, API keys, or Authorization headers.
- LLM keys required for live investigate (`GEMINI_API_KEY`). Heuristic is test-only (`DEVOPSPILOT_FORCE_HEURISTIC`).
- Bind default demo to localhost in README.
