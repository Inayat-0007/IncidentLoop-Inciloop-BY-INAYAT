---
name: add-endpoint
description: Add an HTTP endpoint API-first. Use when creating or changing REST routes, handlers, or OpenAPI operations.
---

# Add endpoint

## Sequence

1. Update `contracts/openapi.yaml`.
2. Implement FastAPI handler in `backend/` with Pydantic models aligned to the contract.
3. Positive test and negative authz test for mutating routes.
4. Run `pytest` and `ruff check backend mcp_server tests`.

## Do not

- Invent a route that is not in OpenAPI.
- Execute rollback from the LangGraph nodes.
- Return stack traces.
