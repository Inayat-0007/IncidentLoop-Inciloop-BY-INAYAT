# Pinned stack — DevOpsPilot

Do not add frameworks that are not listed. Forbidden alternatives are explicit. Versions are **major.minor** pins; exact versions live in `requirements.txt` / `frontend/package-lock.json`.

## Runtime

| Piece | Pin | Notes |
|---|---|---|
| Language | Python **3.12** | `.python-version` |
| HTTP | **FastAPI** 0.115+ | Pydantic v2 models |
| Validation | **Pydantic** 2.10+ | Decision and API schemas |
| Agent graph | **LangGraph** 1.x | One LLM, six nodes |
| LLM adapters | **LangChain** 1.x + `langchain-openai` / `langchain-google-genai` | Lazy import; heuristic if no key |
| RAG | **ChromaDB** 1.x | Deterministic hash embeddings so CI/Docker work offline |
| HTTP client | **httpx** 0.28 | Optional; tools prefer in-process sim |
| MCP | **mcp** 2.x | Stdio server in `mcp_server/` |
| Tests | **pytest** 8+ / 9 | Fixed scenario suite |
| Lint | **ruff** | `ruff check` |

**Forbidden:** Django, Flask, Express, Nest, Hono, Next.js as the product UI, Prisma, MongoDB, Redux.

## LLM

Vendor-neutral. Resolve in this order:

1. `GEMINI_API_KEY` → Gemini via `langchain-google-genai`
2. `OPENAI_API_KEY` → OpenAI via `langchain-openai`
3. `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_DEPLOYMENT` → Azure OpenAI
4. None of the above → **deterministic heuristic** (required for tests and Docker)

Never fail process startup because a paid API key is missing.

## Web (`frontend/`)

| Piece | Pin |
|---|---|
| Bundler | **Vite** 6 |
| UI | **React** 19 + TypeScript 5 |
| HTTP | `fetch` to OpenAPI paths |

**Forbidden:** Next.js, Vue, Svelte, `dangerouslySetInnerHTML` without a sanitizer ADR.

## Data

| Piece | Pin |
|---|---|
| Memory | JSON file + SQLite (`data/memory.sqlite`) |
| Vectors | Chroma persist under `data/chroma/` (gitignored) |
| Knowledge | Markdown under `knowledge/` |

**Forbidden:** MongoDB, cloud-only vector DBs as a hard dependency, production Postgres requirement for MVP.

Markdown is the knowledge format (not PDF) so ingest stays dependency-light and reviewable in git. `backend/rag/ingest.py` loads `.md` (and `.txt`). See ADR 0001.

## Hosting / local

| Piece | Pin |
|---|---|
| Local | Docker Compose: API (serves UI if built) |
| CI | GitHub Actions, Python 3.12 |

## Lockfile strategy

- Commit `requirements.txt` with pinned versions.
- Frontend: commit `package-lock.json` if `npm install` is run.
- New names: skill `verify-deps` → `ALLOWED_DEPS.md` → `python scripts/verify_allowed_deps.py`.
