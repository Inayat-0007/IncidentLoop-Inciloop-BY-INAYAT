# Allowed dependencies

Lockfile strategy: pin versions in `requirements.txt`. CI runs `python scripts/verify_allowed_deps.py`. New names require this file + registry existence check (skill `verify-deps`) in the same PR.

Registry: `https://pypi.org` for Python; `https://registry.npmjs.org` for the Vite frontend.

## PyPI (name must match exactly)

| Package | Registry | Why |
|---|---|---|
| fastapi | PyPI | HTTP API |
| uvicorn | PyPI | ASGI server |
| pydantic | PyPI | Schemas |
| pydantic-settings | PyPI | Env settings |
| langgraph | PyPI | Agent graph |
| langchain | PyPI | LLM utilities |
| langchain-core | PyPI | Messages / core |
| langchain-openai | PyPI | OpenAI / Azure adapter |
| langchain-google-genai | PyPI | Gemini adapter |
| chromadb | PyPI | RAG store |
| httpx | PyPI | HTTP client |
| pytest | PyPI | Tests |
| ruff | PyPI | Lint |
| mcp | PyPI | MCP server |
| python-dotenv | PyPI | Local env load |
| starlette | PyPI | Transitive FastAPI (explicit allow) |

## npm (frontend only)

| Package | Registry | Why |
|---|---|---|
| react | npm | UI |
| react-dom | npm | UI |
| typescript | npm | Types |
| vite | npm | Bundler |
| @vitejs/plugin-react | npm | React plugin |
| @types/react | npm | Types |
| @types/react-dom | npm | Types |

Do not add packages outside these tables without updating them first.

Transitive dependencies installed by pip/npm are allowed only as dependencies of the names above. Direct imports in first-party code must be allowlisted.
