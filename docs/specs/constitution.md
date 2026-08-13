# Engineering constitution — DevOpsPilot

This is the Spec-Driven Development constitution. Chat does not override it.

## Principles

1. **Executable intent.** Specs, OpenAPI, and ADRs are source of truth.
2. **API-first.** No route exists unless it is in `contracts/openapi.yaml`.
3. **Small diffs** unless the human expands the spec (this MVP rewrite is an explicit expansion).
4. **Security is tests.** Unauthorized rollback denials are CI.
5. **No second architecture.** Stack is `docs/STACK.md`.
6. **Human review on contracts, policy gate, and authz.**

## Quality gates

- `ruff check backend mcp_server tests`
- `pytest`
- `python scripts/verify_allowed_deps.py`
- secret scan workflow
- SAST workflow (advisory)

## Security non-negotiables

- Mutating routes require `ROLLBACK_TOKEN` and explicit `authorized: true`.
- Secrets only from environment; never in source, logs, or client bundles.
- The graph must not execute rollback.
- Do not disable the policy gate to make a test pass.
- Do not skip or delete failing assertions.

## Generated files

Do not hand-edit large Chroma persist directories. Knowledge source of truth is `knowledge/**/*.md`.
