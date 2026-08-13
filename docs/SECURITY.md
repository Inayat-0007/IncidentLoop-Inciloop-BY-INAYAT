# Security

- Secrets from `.env` only. Names in `.env.example`.
- `ROLLBACK_TOKEN` required for mutations.
- Do not log tokens, API keys, or Authorization headers.
- LLM keys optional; heuristic path required.
- Bind default demo to localhost in README.
