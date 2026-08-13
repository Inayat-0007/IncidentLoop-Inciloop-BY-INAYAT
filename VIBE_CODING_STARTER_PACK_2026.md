# Full-Stack Vibe-Coding Starter Pack (2026)

**Audience:** engineers using Cursor / LLM coding agents who still want production software, not a weekend demo.  
**Purpose:** one file that tells you *which files to create before any application code*, what belongs in each, and which 2025–2026 failure modes they exist to kill.  
**Stance:** Karpathy coined “vibe coding” as *forget the code exists*. This pack is the opposite operating model: **agentic engineering with executable intent**. The agent writes most of the code. You own spec, architecture, security, and verification.

This document is not an app. Do not start `npm create` until the files in §4 exist at least as stubs with real decisions in them.

---

## 1. Executive brief

A 2026 coding agent is a high-throughput intern with no institutional memory, no fear, and a strong bias to make the tests go green. That intern will:

- invent APIs and packages that do not exist,
- strip auth to “fix” a failing request,
- grow a second architecture beside the first,
- leak secrets into `.env` *and* git history,
- and declare victory when unit tests pass.

The industry name for prompt-and-accept-all is **vibe coding** (Karpathy, Feb 2025). Martin Fowler’s 2025–2026 distinction still holds: vibe coding forgets the code exists and is for disposable software; **agentic programming** still reviews structure, contracts, and risk ([Fowler, *Vibe Coding*](https://martinfowler.com/bliki/VibeCoding.html)).

This starter pack is **context engineering in the repo**: a small, high-signal set of files the agent loads (or retrieves just-in-time) so it does not have to guess. Prompt engineering still matters for a single turn. It does not survive a 40-step agent loop. Anthropic’s 2025 engineering note is the design constraint: context is a finite attention budget; fill it with the smallest high-signal set that raises the odds of the desired outcome ([Anthropic, *Effective context engineering for AI agents*, 2025](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).

**What this pack is for**

- Greenfield full-stack (SPA/SSR + API + DB + CI).
- Brownfield “add a feature without inventing a new stack.”
- Teams mixing Cursor, Claude Code, Codex, Copilot — one vendor-neutral `AGENTS.md`, Cursor-scoped `.mdc` rules, on-demand skills.

**What this pack is not**

- A substitute for human review. SUSVIBES (ICML 2026) showed functional correctness ≠ security: SWE-Agent + Claude 4 Sonnet ~61% functionally correct, ~10.5% secure ([Zhao et al., arXiv:2512.03262](https://arxiv.org/abs/2512.03262)).
- A dump of your entire wiki into the context window. Cursor’s own rule guidance: keep rules under ~500 lines, split them, point at canonical files rather than pasting style guides ([Cursor docs: Rules](https://cursor.com/docs/rules)).

---

## 2. 2026 research synthesis (what is actually proven)

Claims below are tied to named sources. Uncited operational advice is marked **architect practice**.

### 2.1 The term, and why it fails in production

Andrej Karpathy (2 Feb 2025) defined vibe coding as accepting diffs unread, pasting errors back with no comment, and working around bugs with random changes — fine for throwaway projects ([Karpathy / X, archived](https://archive.ph/yNSTA); [MIT Technology Review, Apr 2025](https://www.technologyreview.com/2025/04/16/1115135/what-is-vibe-coding-exactly/); [Wikipedia, *Vibe coding*](https://en.wikipedia.org/wiki/Vibe_coding)). Fowler (2025) adds: maintainability, correctness, security; hallucinated behavior; non-determinism that mutates unrelated code ([Fowler](https://martinfowler.com/bliki/VibeCoding.html)).

GitHub (Sep 2025) described the same failure as treating agents like search engines instead of literal pair programmers: vague prompts force thousands of unstated assumptions ([GitHub Blog, Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)).

### 2.2 Functionality is not safety

| Finding | Source |
|---|---|
| Agent-generated feature work on real repos: high functional success, low secure success (~61% vs ~10.5% in the cited SWE-Agent + Claude 4 Sonnet setting). Vulnerability hints in the prompt did not fix it. | Zhao et al., *Is Vibe Coding Safe? SUSVIBES*, arXiv:2512.03262 (Dec 2025); ICML 2026 poster |
| ~45% of AI-generated samples introduce known security flaws when no security guidance is given; syntax correctness >95%; security pass rate stuck ~55% through Spring 2026. XSS (CWE-80) ~15% pass; log injection (CWE-117) ~13% pass. Java worst (~29%). | Veracode, *Spring 2026 GenAI Code Security Update* (24 Mar 2026) |
| CSA note: Veracode’s 100+ model / 80-task series; Java ~72% failure in earlier cycle; CVE tracking of AI-attributed issues rising in early 2026; Cursor MCP-related CVEs in 2025 (e.g. CurXecute CVE-2025-54135). | [CSA research note, 2026](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-generated-code-vulnerability-surge-2026/) |
| Common generated-code holes: missing validation, injection, broken authz, hardcoded credentials, hallucinated deps (“slopsquatting”). | Endor Labs overview; Cycode 2026 AI vuln roundup |

**Implication:** “Make it secure” in the user prompt is not a control. SUSVIBES tried hints. Veracode tested unprompted generation. You need **invariants in contracts + negative tests + SAST/secret scan in CI**, not slogans in chat.

### 2.3 Hallucinated packages (slopsquatting)

Spracklen et al., USENIX Security 2025 (*We Have a Package for You!*): large-scale package-name hallucination on PyPI/npm (reported ~19.7% of samples with ≥1 hallucinated package in that study). 2026 replication on frontier models: hallucination rates compressed to ~4.6–6.1%, **not zero**; 127 names invented identically by all five evaluated models ([arXiv:2605.17062](https://arxiv.org/pdf/2605.17062)). CSA (Apr 2026): real malicious packages on this vector with tens of thousands of downloads ([CSA slopsquatting note](https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419-csa/)).

**Implication:** lockfiles, an allowed-dependency list, and a CI check that every install name exists on the intended registry *before* the agent’s `npm i` / `pip install` is trusted.

### 2.4 Agent failure is a process, not a score

- **Epistemic errors early, hidden until unrecoverable.** 1,794 Terminal-Bench trajectories, 14 findings: failures often start in the first few steps ([*Failure as a Process*, arXiv HTML 2607.09510](https://arxiv.org/html/2607.09510v1)).
- **Operational safety on benign tasks:** constraint violations, destructive ops, auth bypass, deception; 547 confirmed GitHub incidents, 326 high/critical; >65% in bugfix/setup ([*What Breaks When LLMs Code?*, arXiv:2605.30777](https://arxiv.org/abs/2605.30777)).
- **Underspecification vs capability vs harness.** ClayBuddy / AgentArmor: extended system prompt, command classifier, 3-strikes, deterministic guardrails, tools to edit own context ([arXiv HTML 2606.19380](https://arxiv.org/html/2606.19380)).
- **Architecture/domain gaps, not just hard patches.** 9,374 trajectories: never-solved “easy” tasks fail on architectural reasoning; gather-context-then-edit + validation correlates with success ([arXiv:2604.02547](https://arxiv.org/abs/2604.02547)).
- **Agent PRs on GitHub:** docs/CI merge more; bugfix/perf merge less; not-merged PRs are larger, fail CI, or implement unwanted features; reviewer abandonment is common ([arXiv HTML 2601.15195](https://arxiv.org/html/2601.15195v1)).

**Implication:** validate *before* the agent’s first edit (spec, stack, threat model). Keep PRs small. CI must exist *before* the agent “finishes.” Destructive shell needs hooks, not a polite AGENTS.md sentence.

### 2.5 Benchmarks lie about production

SWE-bench Verified saturation/contamination was widely reported in 2026 commentary (OpenAI retiring it as a frontier eval; SWE-bench Pro much harder; METR-style human review that many passing patches would not merge). Treat blog numbers as industry reporting, not as a single canonical paper. A cleaner academic signal: **SWE-EVO** — long-horizon evolution vs isolated bugfix: gpt-5.2 ~72.8% SWE-Bench Verified vs ~22.9% SWE-EVO; best model ~25% on SWE-EVO ([arXiv:2512.18470](https://arxiv.org/abs/2512.18470)).

**Implication:** your repo’s tests, contracts, and ADRs *are* the benchmark. Isolated unit tests that the agent wrote to match its own code are not.

### 2.6 Context engineering vs prompt engineering

Prompt = how you ask this turn. Context = everything in the window: system, rules, retrieved files, tools, history ([Anthropic 2025](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents); [Elasticsearch Labs](https://www.elastic.co/search-labs/blog/context-engineering-vs-prompt-engineering); [Atlan 2026](https://atlan.com/know/context-engineering-vs-prompt-engineering/)). Karpathy / Tobi Lütke popularized the “fill the window with the right tokens” framing in 2025.

Cursor’s 2026 agent guide: Plan Mode first; save plans to `.cursor/plans/`; start a new chat on task boundaries; long chats accumulate noise; Rules = static, Skills = on-demand ([Cursor, *Best practices for coding with agents*](https://cursor.com/blog/agent-best-practices)). Anthropic later pushed **progressive disclosure** (skills/tools loaded when needed; bloated CLAUDE.md can *hurt* stronger models) ([Claude blog, context engineering for Claude 5-generation](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)).

### 2.7 Spec-driven development is the industry counter-move

Microsoft (Jun 2026): Spec-Driven Development — constitution → specify → clarify → plan → tasks → implement → validate. Spec quality = output quality. Prompt-first loses intent across handoffs ([Microsoft, SDD](https://developer.microsoft.com/blog/spec-driven-development-ai-native-engineering/)). GitHub Spec Kit (Sep 2025): specify / plan / tasks / implement with checkpoints ([GitHub Blog](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)).

### 2.8 Cursor / agent file conventions (verified 2026)

From [Cursor Rules docs](https://cursor.com/docs/rules), [Skills docs](https://cursor.com/docs/skills), [MCP docs](https://cursor.com/docs/mcp), [Hooks docs](https://cursor.com/docs/hooks.md), [agents.md](https://agents.md/):

| Artifact | Status | Role |
|---|---|---|
| `.cursor/rules/*.mdc` | **Primary Cursor mechanism** | YAML frontmatter: `alwaysApply`, `globs`, `description`. Plain `.md` in that folder is **ignored**. |
| `AGENTS.md` | **Vendor-neutral standard** (Agentic AI Foundation / Linux Foundation; Cursor, Codex, Copilot, Jules, Amp, …) | Plain markdown. Nested files: closer file wins on conflict. README is for humans; AGENTS.md is for agents. |
| `CLAUDE.md` | Claude Code native; Cursor also reads it | Always-on in Cursor if present — easy leak of Claude-only workflow into Cursor. Prefer thin pointer to AGENTS.md. |
| `.cursorrules` | **Legacy** | Migrate to `.mdc` / AGENTS.md; delete to stop drift. |
| `.cursor/skills/*/SKILL.md` or `.agents/skills/` | On-demand workflows | Frontmatter `name`, `description`, optional `paths`. Scripts/references/assets loaded progressively. |
| `.cursor/hooks.json` | Lifecycle control | `beforeShellExecution`, `beforeMCPExecution`, `afterFileEdit`, secret scan, etc. Cloud agents pick up repo hooks. |
| `.cursor/mcp.json` | Project MCP | Use `${env:NAME}` interpolation; never hardcode keys. Allowlist servers. |
| Team Rules | Dashboard | **Team > Project > User** when guidance conflicts. |

Cursor official rule hygiene: focused, actionable, examples via `@file` references, don’t paste entire style guides (linters exist), don’t list every CLI the model already knows.

---

## 3. The rule: no application code until intent is executable

**Architect practice.** An agent that starts in an empty folder will pick a stack from training-set fashion, invent folder layout, skip auth, and generate 4,000 lines you now own.

**Definition of “allowed to write app code”:**

1. Product intent is written (who, problem, non-goals, acceptance tests).
2. Stack is *pinned* (language, framework, DB, auth, hosting) with versions.
3. Architecture is drawn at C4 context + container level; one ADR for the risky choices.
4. API and data contracts exist (OpenAPI or equivalent + schema).
5. Threat model lists assets, trust boundaries, and “never do X.”
6. Agent operating contract exists (`AGENTS.md` + scoped rules + at least one security skill).
7. CI, secrets policy, and `.env.example` exist so “done” is mechanical.

Microsoft SDD and GitHub Spec Kit both encode the same gate: do not implement until specify + plan survive human critique.

If you are truly prototyping disposable software (Fowler’s allowed case), skip to a 1-page PRD + `AGENTS.md` + `.gitignore` + `.env.example`. Do not skip those four.

---

## 4. Complete starter-pack file tree

Opinionated full-stack layout (TypeScript monorepo shown; swap names, keep *roles*). Files marked **P0** are mandatory before app code. **P1** before first merge to `main`. **P2** before production traffic.

```text
repo/
├── README.md                          # P0 humans
├── AGENTS.md                          # P0 all agents
├── CLAUDE.md                          # P1 thin pointer only if you use Claude Code
├── LICENSE
├── .gitignore                         # P0
├── .editorconfig                      # P1
├── .nvmrc | .python-version           # P0 pin runtime
├── .env.example                       # P0 never real secrets
├── .env                               # never commit
│
├── .cursor/
│   ├── rules/
│   │   ├── 00-constitution.mdc        # P0 alwaysApply
│   │   ├── stack.mdc                  # P0 alwaysApply (short; points to docs/STACK.md)
│   │   ├── security.mdc               # P0 alwaysApply
│   │   ├── no-overgeneration.mdc      # P0 alwaysApply
│   │   ├── frontend.mdc               # P0 globs apps/web/**
│   │   ├── backend.mdc                # P0 globs apps/api/**
│   │   ├── database.mdc               # P0 globs **/prisma/**, **/migrations/**
│   │   └── testing.mdc                # P0 globs **/*.{test,spec}.*
│   ├── skills/
│   │   ├── add-endpoint/SKILL.md      # P1
│   │   ├── add-migration/SKILL.md     # P1
│   │   ├── threat-pass/SKILL.md       # P1
│   │   └── verify-deps/SKILL.md       # P0
│   ├── hooks.json                     # P1
│   ├── hooks/
│   │   ├── block-secrets.sh
│   │   └── allow-install.sh
│   ├── mcp.json                       # P1 if MCP used
│   └── plans/                         # generated; gitignore or commit by policy
│
├── docs/
│   ├── PRD.md                         # P0
│   ├── STACK.md                       # P0
│   ├── ARCHITECTURE.md                # P0 C4 context + containers
│   ├── CONTEXT.md                     # P0 system context, actors, trust
│   ├── DATA_MODEL.md                  # P0
│   ├── API.md                         # P0 index → openapi
│   ├── THREAT_MODEL.md                # P0
│   ├── SECURITY.md                    # P0
│   ├── RUNBOOK.md                     # P1
│   ├── OBSERVABILITY.md               # P1
│   ├── ADR/
│   │   ├── 0000-template.md
│   │   └── 0001-stack.md              # P0
│   ├── specs/
│   │   ├── constitution.md            # P0 SDD
│   │   ├── 0001-mvp.md                # P0
│   │   └── 0001-plan.md               # P0
│   └── runbooks/
│       └── incident.md                # P1
│
├── contracts/
│   ├── openapi.yaml                   # P0
│   ├── asyncapi.yaml                  # P2 if events
│   └── json-schema/                   # P0 shared types
│
├── apps/
│   ├── web/
│   │   ├── AGENTS.md                  # P1 nested
│   │   ├── package.json
│   │   └── src/                       # empty until P0 docs exist
│   └── api/
│       ├── AGENTS.md
│       ├── package.json
│       └── src/
│
├── packages/
│   └── shared-types/                  # generated from contracts (P1)
│
├── infra/
│   ├── README.md                      # P1
│   └── compose.yaml                   # P1 local db/redis
│
├── .github/                           # or .gitlab-ci.yml
│   ├── CODEOWNERS                     # P1
│   ├── dependabot.yml | renovate      # P1
│   └── workflows/
│       ├── ci.yml                     # P0
│       ├── secret-scan.yml            # P0
│       └── sast.yml                   # P1
│
├── scripts/
│   ├── verify-allowed-deps.mjs        # P0
│   └── check-no-secrets.sh
│
├── ALLOWED_DEPS.md                    # P0
├── package.json                       # workspace root
├── pnpm-workspace.yaml | turbo.json
├── tsconfig.base.json
├── eslint.config.js                   # P0
├── prettier.config.js
├── vitest.workspace.ts | playwright.config.ts
└── COMMITLINT / lefthook / husky      # P1
```

GitLab equivalent: `.gitlab-ci.yml` + `CODEOWNERS` at root. Same gates.

---

## 5. File-by-file: purpose, outline, failure it prevents

For each file: **purpose**, **required content**, **2026 failure**.

### 5.1 Human + agent entry

#### `README.md` (P0)

**Purpose:** humans. Install, run, architecture pointer. Not a second AGENTS.md.

**Content outline**

- What this product is (one paragraph)
- Prerequisites (runtime versions — point at `.nvmrc`)
- `pnpm install` / `pnpm dev` / `pnpm test` / `pnpm lint`
- Repo map (apps/web, apps/api)
- Link to `docs/PRD.md`, `docs/ARCHITECTURE.md`, `AGENTS.md`
- Security: never commit `.env`; see `docs/SECURITY.md`

**Prevents:** agents stuffing operational contract into README (agents.md standard: README stays human). Humans who cannot run the app “vibe” around broken setup — the #1 cluster in operational-safety incident studies (setup/config).

#### `AGENTS.md` (P0) — canonical agent contract

**Purpose:** vendor-neutral facts every agent needs: layout, commands, never-dos, where truth lives. Plain markdown, no frontmatter ([agents.md](https://agents.md/)). Keep it **short** (architect practice: ~80–200 lines). Details live in `docs/` and skills.

**Content outline (use these headings)**

```markdown
# Agent operating contract

## Product
- One-line description + link to docs/PRD.md
- Non-goals (explicit)

## Stack (pinned)
- Point to docs/STACK.md. Do not invent libraries.

## Layout
- apps/web, apps/api, contracts/, docs/

## Commands (exact)
- Install, dev, test, typecheck, lint, db migrate
- Prefer single-file tests while iterating

## Source of truth
- API: contracts/openapi.yaml
- Data: docs/DATA_MODEL.md + migrations
- Decisions: docs/ADR/
- Specs: docs/specs/

## Invariants (never violate)
- Authz on every mutating route
- No new dependencies without ALLOWED_DEPS.md + lockfile
- No secrets in source, logs, or client bundles
- Do not “fix” failing tests by deleting assertions or skipping auth

## Workflow
- Read the spec and ADR for the area before editing
- Plan Mode / write a plan for anything >1 file
- Typecheck + tests before claiming done
- Small diffs; no drive-by refactors

## PR
- Conventional commits: feat|fix|chore|docs|refactor|test
- Title: [<area>] <imperative>
```

**Prevents:** context drift (every agent gets the same facts); inconsistent stack; missing architecture pointers; “delete the test to go green”; secret leaks via “just hardcode for now.” Nested `apps/web/AGENTS.md` overrides locally (Cursor + agents.md spec).

#### `CLAUDE.md` (P1, optional)

**Content:** `Read ./AGENTS.md first. It is canonical.` Then only Claude Code permissions/hooks that Cursor should *not* treat as universal. Cursor reads CLAUDE.md always ([DEV 2026 roundup on precedence](https://dev.to/rulestack/agentsmd-vs-claudemd-vs-cursorrules-what-cursor-actually-reads-now-and-in-what-order-17bo)) — keep it thin.

**Prevents:** config drift between tools.

#### `.cursorrules`

**Do not create.** Legacy. Conflicts with `.mdc`.

---

### 5.2 Cursor-specific: rules, skills, hooks, MCP

#### `.cursor/rules/00-constitution.mdc` (P0)

```yaml
---
alwaysApply: true
---
```

**Content:** 15–40 bullets max. Project invariants, “read before write,” “do not modify generated files,” “when unsure, read source,” pointer to `docs/specs/constitution.md`. No style-guide novel.

**Prevents:** over-generation; agents “helpfully” rewriting unrelated modules (Fowler non-determinism). Matches Cursor alwaysApply semantics ([docs](https://cursor.com/docs/rules)).

#### `.cursor/rules/stack.mdc` (P0, `alwaysApply: true`)

**Content:** “Stack is defined in `docs/STACK.md`. Do not add frameworks. Allowed packages: `ALLOWED_DEPS.md`. Verify registry names exist (skill `verify-deps`).”

**Prevents:** hallucinated APIs/packages; inconsistent stack.

#### `.cursor/rules/security.mdc` (P0, `alwaysApply: true`)

**Content:** parameterized queries; output encoding; authn/authz checks on every route; no `dangerouslySetInnerHTML` without sanitizer; no logging of tokens/PII; secrets from env only; negative tests for unauthorized access. Point to `docs/THREAT_MODEL.md`.

**Prevents:** Veracode XSS/log-injection failure modes; SUSVIBES “strip auth to make it work”; hardcoded credentials.

#### `.cursor/rules/no-overgeneration.mdc` (P0, `alwaysApply: true`)

**Content:** change only files required by the spec/task; no new folders without ADR; no extra features; no README novels; if the task is “add field X,” do not rebuild the design system.

**Prevents:** unwanted features in agent PRs (GitHub agent-PR study); SWE-EVO-style long-horizon drift.

#### `.cursor/rules/frontend.mdc` (P0)

```yaml
---
description: Web app UI conventions
globs: apps/web/**
alwaysApply: false
---
```

**Content:** component library, routing, state, how to call the API (generated client only), accessibility, “no fetch to ad-hoc URLs.” `@` a canonical component.

**Prevents:** second UI stack; hallucinated frontend SDKs; skipping the OpenAPI client.

#### `.cursor/rules/backend.mdc` (P0)

`globs: apps/api/**`

**Content:** handler → service → repo; validate with the shared schema; errors as `{code, message}`; never return stack traces; pagination defaults.

**Prevents:** accidental architecture; business logic in route files; leaking internals.

#### `.cursor/rules/database.mdc` (P0)

`globs: **/migrations/**,**/prisma/**,**/drizzle/**`

**Content:** expand/contract migrations; never destructive down on prod; PII columns listed; no `migrate reset` in shared envs.

**Prevents:** destructive operations (operational safety paper); data-loss “fixes.”

#### `.cursor/rules/testing.mdc` (P0)

`globs: **/*.{test,spec}.*`

**Content:** test behavior and authz, not implementation; no `it.skip` to green CI; include at least one negative authz test per new endpoint; no network in unit tests; flaky = fail, don’t retry-loop in CI without quarantine policy.

**Prevents:** flaky tests; agent-written tests that only assert the agent’s own mocks; SUSVIBES-style “functional but insecure.”

**Architect practice:** glob-scoped rules beat a 2,000-line always-on file (context rot). Cursor: rules do not affect Tab autocomplete; User Rules don’t apply to Cmd/Ctrl+K.

#### Skills (P0–P1)

Each skill: folder + `SKILL.md` with `name` + `description` ([Cursor skills](https://cursor.com/docs/skills)). Put procedures here, **not** in always-on rules.

**`.cursor/skills/verify-deps/SKILL.md` (P0)**

- When: adding/changing dependencies, or agent wants to `npm i` / `pip install`.
- Instructions: check `ALLOWED_DEPS.md`; query official registry; refuse names not on registry; run `scripts/verify-allowed-deps.mjs`.
- **Prevents:** slopsquatting / package hallucination.

**`.cursor/skills/add-endpoint/SKILL.md` (P1)**

- Sequence: update `contracts/openapi.yaml` → generate types → implement handler → positive + negative tests → do not skip OpenAPI.
- **Prevents:** hallucinated routes that don’t match the client; missing authz.

**`.cursor/skills/add-migration/SKILL.md` (P1)**

- Expand/contract; update DATA_MODEL.md; never edit old migration files that shipped.
- **Prevents:** irreversible schema “fixes.”

**`.cursor/skills/threat-pass/SKILL.md` (P1)**

- For every feature: map to THREAT_MODEL.md; add abuse cases; add negative tests.
- **Prevents:** “security as a comment in the prompt” (SUSVIBES).

Optional: `scripts/` inside the skill for deterministic checks (AgentArmor-style: don’t rely on the model to obey prose).

#### `.cursor/hooks.json` + `hooks/` (P1)

**Purpose:** deterministic control of the agent loop ([Cursor hooks](https://cursor.com/docs/hooks.md)). Prose “please don’t” is not a control (ClayBuddy: harness errors vs capability errors).

**Minimum hooks**

| Event | Action |
|---|---|
| `beforeShellExecution` | Block `rm -rf`, `git push --force`, `curl \| sh`, prod migrate, install of packages not in allowlist |
| `afterFileEdit` | Secret/PII regex scan; fail closed |
| `beforeMCPExecution` | Allowlist MCP server+tool; block Slack/email send in prod tokens |
| `sessionStart` | Inject “read AGENTS.md + current spec” reminder (keep tiny) |

Cloud agents load `.cursor/hooks.json` from repo root — put security hooks in-repo, not only on one laptop.

**Prevents:** destructive ops; secret leaks; MCP prompt-injection blast radius (CSA/Cursor CVE class).

#### `.cursor/mcp.json` (P1 if used)

**Content:** only needed servers; `"env": { "API_KEY": "${env:GITHUB_TOKEN}" }`; no inline secrets ([Cursor MCP](https://cursor.com/docs/mcp)). Document in `docs/SECURITY.md` which servers are approved.

**Prevents:** tool sprawl (context bloat), token leak in git, untrusted MCP (CurXecute-class risk). Cursor’s own MCP security notes: verify source, least privilege, audit.

#### `.cursor/plans/` (workflow)

Cursor Plan Mode can save plans here ([agent best practices](https://cursor.com/blog/agent-best-practices)). **Architect practice:** commit plans that correspond to `docs/specs/*-plan.md`, or ignore scratch plans. Do not let the chat be the only plan (chat is the worst memory).

---

### 5.3 Architecture / spec files

#### `docs/specs/constitution.md` (P0)

SDD constitution ([Microsoft SDD](https://developer.microsoft.com/blog/spec-driven-development-ai-native-engineering/)): principles, quality gates, “we do not ship without X.”

**Outline:** engineering principles; required gates (typecheck, test, SAST, secret scan); API-first; security non-negotiables; size of PRs.

**Prevents:** missing architecture as a social problem — nobody agreed the rules.

#### `docs/PRD.md` (P0)

**Outline**

- Problem, users, JTBD
- In-scope MVP / out-of-scope
- User journeys (happy + failure)
- Acceptance criteria (Given/When/Then)
- Analytics / success metrics
- Open questions (must be empty or dated)

**Prevents:** translation loss (Microsoft SDD); unwanted features; agents filling ambiguity with training-set SaaS clones.

#### `docs/specs/0001-mvp.md` + `0001-plan.md` (P0)

Spec Kit shape: *what/why* in spec; *how/stack/constraints* in plan; then tasks.

**Prevents:** prompt-first drift; long-horizon SWE-EVO failure (no durable intent).

#### `docs/STACK.md` (P0)

**Outline:** language + version; package manager; web framework; API framework; ORM; DB; cache; auth; hosting; observability; **forbidden** alternatives (“do not introduce Redux if we use TanStack Query”). Pin major.minor.

**Prevents:** inconsistent stack; hallucinated libraries.

#### `docs/ADR/0001-stack.md` (P0) + `0000-template.md`

**Template:** Status, Context, Decision, Consequences, Alternatives rejected.

**Prevents:** “no ADRs” — agents re-litigate React vs Vue every session. Beyond Resolution Rates: architectural reasoning gaps.

#### `docs/ARCHITECTURE.md` + `docs/CONTEXT.md` (P0)

C4 **context** (people/systems) + **containers** (web, api, db, queue). Sequence for the critical path (login, money-move, incident ingest — whatever your product is). Trust boundaries.

**Prevents:** accidental architecture; agents adding a second backend.

#### `docs/DATA_MODEL.md` (P0)

Entities, fields, types, uniqueness, PII flags, retention, relationships. Point at migrations as executable truth.

**Prevents:** invented columns; GDPR accidents; ORM hallucination.

#### `contracts/openapi.yaml` (P0)

Every public HTTP route: auth scheme, request/response schemas, error codes, pagination. Frontend consumes generated types only.

**Prevents:** hallucinated endpoints; FE/BE drift; missing 401/403 contracts (negative tests hang off this).

#### `docs/THREAT_MODEL.md` (P0)

**Outline:** assets; actors; entry points; STRIDE or lightweight abuse cases; trust boundaries; **explicit insecure shortcuts the agent must never take** (disable auth, `CORS *` with credentials, raw SQL string concat).

**Prevents:** Veracode/SUSVIBES security gap. Hints in chat failed; a durable threat model + tests is the control.

#### `docs/SECURITY.md` (P0)

Secret handling; env var list (names only); dependency policy; SAST tools; how to report vulns; MCP allowlist.

#### `docs/RUNBOOK.md` + `docs/OBSERVABILITY.md` (P1)

How to boot local; how to read logs; SLO; on-call; rollback. Agents invent `console.log` archaeology without this — and lie about “deployed successfully” (deception category in operational-safety paper).

---

### 5.4 Engineering guardrails (deterministic)

These are not “AI files.” They are why the pack works. Agents optimize for whatever the harness *actually* blocks.

| File | Content | Failure prevented |
|---|---|---|
| `.gitignore` | `.env`, keys, `node_modules`, agent junk, `.cursor/plans/*.scratch.md` if needed | secret leaks |
| `.env.example` | All var **names** + dummy values; comments for where to get real values | agent invents `POSTGRES_PASSWORD=postgres` in committed files |
| `.nvmrc` / runtime pin | Exact Node/Python | “works on my agent sandbox” |
| `ALLOWED_DEPS.md` | Name, registry, why | slopsquatting |
| lockfiles | Commit them | floating malicious latest |
| `eslint` + `tsconfig` strict | `no-explicit-any` policy, etc. | type holes agents love |
| `ci.yml` | lint, typecheck, unit, contract tests, `verify-allowed-deps` | agent PRs that don’t pass CI (GitHub study) |
| `secret-scan.yml` | gitleaks/trufflehog | CWE-798 |
| `sast.yml` | Semgrep/CodeQL/Veracode-class | XSS/injection the model won’t see |
| `CODEOWNERS` | `contracts/**` and `docs/ADR/**` require a human | silent contract mutation |
| conventional commits + commitlint | `feat/fix/chore/...` | noisy agent commit spam |
| Dependabot/Renovate | Controlled updates | stale vulnerable deps (Endor/CSA supply chain) |
| Playwright/integration | Critical journeys + **authz denials** | functional-only green |
| `lefthook`/`husky` | pre-commit secret scan + lint staged | leaks before push |

**Architect practice:** put the same commands in `AGENTS.md` that CI runs. Agents will try to execute them if listed ([agents.md FAQ](https://agents.md/)).

---

## 6. How the pack maps onto 2026 failure modes

| Failure | Evidence | Pack control |
|---|---|---|
| Hallucinated APIs / packages | USENIX 2025; arXiv:2605.17062; CSA slopsquatting 2026 | STACK.md, OpenAPI, ALLOWED_DEPS, verify-deps skill, lockfile, install hook |
| Context drift / rot | Anthropic 2025; Cursor long-chat guidance | Short AGENTS.md; glob rules; skills; new chat per task; plans on disk |
| Missing architecture | arXiv:2604.02547; Fowler spaghetti | C4, ADRs, constitution |
| Security holes | SUSVIBES; Veracode Spring 2026 | threat model, security.mdc, negative tests, SAST |
| Flaky / vacuous tests | architect practice + agent PR CI failures | testing.mdc, CI, forbid skip, contract tests |
| Secret leaks | industry + CWE-798 in generated code | gitignore, env.example, hooks, gitleaks |
| Over-generation | agent PR “unwanted features” | no-overgeneration.mdc, specs with non-goals, small tasks |
| Inconsistent stack | GitHub “stack you wouldn’t choose” | STACK.md + alwaysApply stack rule |
| No ADRs | every session re-decides | docs/ADR |
| Destructive shell | arXiv:2605.30777 | hooks beforeShellExecution |
| MCP / tool injection | CVE-2025-54135 class; Cursor MCP warnings | mcp.json interpolation, allowlist, beforeMCPExecution |
| Benchmark theater | SWE-EVO drop; SWE-bench commentary | *your* CI + contracts as eval |
| Early epistemic error | Failure-as-process 2026 | Plan Mode + spec gate before first edit |
| Config drift Cursor vs Claude | 2026 AGENTS.md vs CLAUDE.md guides | AGENTS.md canonical, thin CLAUDE.md |

---

## 7. How a senior architect sequences creation

Do this in order. Do not parallelize “app + docs” — the agent will finish the app first and the docs will be fan fiction.

**Hour 0 — product**

1. `docs/PRD.md` until non-goals and acceptance tests are cruelly specific.
2. `docs/specs/constitution.md` (quality gates).
3. `docs/specs/0001-mvp.md` (journeys only, no stack).

**Hour 1 — constraints**

4. `docs/STACK.md` + `docs/ADR/0001-stack.md` (write the rejected alternatives).
5. `docs/CONTEXT.md` + `docs/ARCHITECTURE.md` (C4).
6. `docs/DATA_MODEL.md` + empty migration policy.
7. `contracts/openapi.yaml` for MVP routes including error schemas.
8. `docs/THREAT_MODEL.md` + `docs/SECURITY.md`.

**Hour 2 — agent harness**

9. `AGENTS.md` (commands may be placeholders until package.json exists — then update).
10. `.cursor/rules/*.mdc` (constitution, stack, security, no-overgeneration, area globs).
11. `verify-deps` skill + `ALLOWED_DEPS.md`.
12. `.gitignore`, `.env.example`, runtime pin.

**Hour 3 — empty executable skeleton (still almost no features)**

13. Workspace `package.json`, lint, typecheck, test runner, CI that runs them on an empty/hello test.
14. Secret scan workflow.
15. `CODEOWNERS`.
16. Nested `apps/*/AGENTS.md` one-pagers.
17. Hooks for shell + secrets.

**Only then**

18. Plan Mode: `0001-plan.md` + task list (one endpoint + one screen at a time).
19. Skill `add-endpoint` for the first route: contract → types → impl → negative test.
20. After the agent repeats a mistake twice, **update a rule or skill**, do not add a longer chat prompt (Cursor: rules when you see repeated mistakes).

**Ongoing**

- New chat per feature (Cursor best practices).
- New ADR when a stack or boundary changes.
- Spec Kit clarify step when the agent asks more than two clarifying questions — the spec was not build-ready (ProductOS 2026: four questions: problem, must-do, constraints, verify).
- Human review of `contracts/**` and authz paths; do not “Accept All” (Karpathy’s joke is the anti-pattern for this pack).

---

## 8. Copy-paste checklist

Print this. Check boxes in the repo, not in your head.

### Before any feature code

- [ ] `README.md` explains run/test for humans
- [ ] `AGENTS.md` has exact commands, invariants, source-of-truth links
- [ ] No `.cursorrules`
- [ ] `.cursor/rules/*.mdc` exist with real frontmatter (not ignored `.md`)
- [ ] `docs/PRD.md` has non-goals + Given/When/Then
- [ ] `docs/STACK.md` pins versions and forbids alternates
- [ ] `docs/ADR/0001-*.md` records the stack decision
- [ ] `docs/ARCHITECTURE.md` + `docs/CONTEXT.md` (C4)
- [ ] `docs/DATA_MODEL.md`
- [ ] `contracts/openapi.yaml` for MVP
- [ ] `docs/THREAT_MODEL.md` includes “agent must not disable auth”
- [ ] `docs/SECURITY.md` + `.env.example` (names only)
- [ ] `ALLOWED_DEPS.md` + lockfile policy
- [ ] `.gitignore` includes `.env` and key material
- [ ] Runtime pin (`.nvmrc` or equivalent)
- [ ] CI: lint, typecheck, test (even if tests are placeholders)
- [ ] CI: secret scan
- [ ] `verify-deps` skill or script in CI

### Before first PR to default branch

- [ ] Nested `AGENTS.md` in apps if monorepo
- [ ] `frontend.mdc` / `backend.mdc` / `testing.mdc` glob-scoped
- [ ] Skills: add-endpoint, add-migration, threat-pass
- [ ] `.cursor/hooks.json` blocks force-push, recursive delete, unapproved installs
- [ ] If MCP: `.cursor/mcp.json` uses `${env:...}`; allowlisted
- [ ] `CODEOWNERS` on contracts and ADRs
- [ ] Conventional commit lint
- [ ] At least one **negative** authz test in CI
- [ ] SAST job (Semgrep/CodeQL/equivalent)
- [ ] `docs/RUNBOOK.md` local + rollback
- [ ] `CLAUDE.md` is a pointer or absent

### Every agent session

- [ ] Spec/plan exists for this change
- [ ] Plan Mode for multi-file work; save plan
- [ ] New chat if previous task ended or agent is looping
- [ ] Diff read by a human on auth, crypto, deps, migrations
- [ ] No new dependency unless registry-verified
- [ ] Typecheck + tests green on the **CI command list**, not a unique local skip
- [ ] Repeated agent mistake → rule/skill update

### Production

- [ ] Threat model reviewed against actual routes
- [ ] Observability: request id, authz denials, error budgets
- [ ] Dependabot/Renovate on
- [ ] Incident runbook
- [ ] MCP/hooks inventory (who can run what)

---

## 9. Templates (fill, don’t invent)

### 9.1 ADR template (`docs/ADR/0000-template.md`)

```markdown
# ADR NNNN: Title

- Status: Proposed | Accepted | Superseded by ADR-XXXX
- Date: YYYY-MM-DD
- Deciders:

## Context
## Decision
## Consequences
## Alternatives considered
## What agents must not do instead
```

### 9.2 Feature spec stub (`docs/specs/NNNN-title.md`)

```markdown
# Spec NNNN: Title

## Problem / user
## In scope / out of scope
## Journeys
## Acceptance criteria (testable)
## API impact (link OpenAPI operations)
## Data impact
## Security / abuse cases
## Observability
## Non-goals
## Open questions (blockers)
```

### 9.3 `.cursor/rules` frontmatter cheat sheet

```markdown
---
alwaysApply: true
---
# constitution — tiny

---
description: Prisma migration rules
globs: **/prisma/**
alwaysApply: false
---

---
description: Use when changing HTTP contracts
alwaysApply: false
---
# agent-decides via description; no globs
```

### 9.4 Skill frontmatter

```markdown
---
name: verify-deps
description: Verify npm/PyPI package names exist and are on ALLOWED_DEPS.md before any install. Use when adding dependencies or running package managers.
---
```

### 9.5 MCP snippet (no secrets)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_TOKEN}" }
    }
  }
}
```

---

## 10. What you should still not automate

**Architect practice**, aligned with the papers:

- Accepting dependency adds without a registry check.
- Production schema destructive changes.
- Authz logic review (models fail dataflow: Veracode XSS/log-injection).
- “The tests pass” as the definition of merge (SWE-bench/METR gap; write tests that encode *your* spec, including denials).
- Dumping the whole pack into `alwaysApply` (you will recreate context rot and fight stronger models that degrade with bloated instructions).

Vibe coding remains valid for throwaway software used by people who accept the risk (Fowler). The moment the software has users, credentials, or a tomorrow, this pack is the minimum architecture of control.

---

## 11. Sources (cited)

**Primary / official**

- Karpathy, A. “vibe coding” post, 2 Feb 2025. [archive.ph/yNSTA](https://archive.ph/yNSTA)
- Fowler, M. *Vibe Coding*. [martinfowler.com/bliki/VibeCoding.html](https://martinfowler.com/bliki/VibeCoding.html) (2025)
- MIT Technology Review. *What is vibe coding, exactly?* 16 Apr 2025. [technologyreview.com](https://www.technologyreview.com/2025/04/16/1115135/what-is-vibe-coding-exactly/)
- Wikipedia. *Vibe coding*. [en.wikipedia.org/wiki/Vibe_coding](https://en.wikipedia.org/wiki/Vibe_coding)
- Anthropic. *Effective context engineering for AI agents*. 29 Sep 2025. [anthropic.com/engineering/effective-context-engineering-for-ai-agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic / Claude. *The new rules of context engineering for Claude 5 generation models*. [claude.com/blog/...](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
- Cursor. *Rules*. [cursor.com/docs/rules](https://cursor.com/docs/rules)
- Cursor. *Agent Skills*. [cursor.com/docs/skills](https://cursor.com/docs/skills)
- Cursor. *MCP*. [cursor.com/docs/mcp](https://cursor.com/docs/mcp)
- Cursor. *Hooks*. [cursor.com/docs/hooks.md](https://cursor.com/docs/hooks.md)
- Cursor. *Best practices for coding with agents*. [cursor.com/blog/agent-best-practices](https://cursor.com/blog/agent-best-practices)
- AGENTS.md standard. [agents.md](https://agents.md/) (Agentic AI Foundation / Linux Foundation)
- GitHub. *Spec-driven development with AI* (Spec Kit). 2 Sep 2025. [github.blog](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- Gupta, A. Microsoft. *Spec-Driven Development: A Spec-First Approach to AI-Native Engineering*. 10 Jun 2026. [developer.microsoft.com](https://developer.microsoft.com/blog/spec-driven-development-ai-native-engineering/)

**Papers / benchmarks**

- Zhao, Wang, Zhang, Luo, Li, Li. *Is Vibe Coding Safe? … SUSVIBES*. arXiv:2512.03262, Dec 2025; ICML 2026. [arxiv.org/abs/2512.03262](https://arxiv.org/abs/2512.03262)
- *SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution*. arXiv:2512.18470. [arxiv.org/abs/2512.18470](https://arxiv.org/abs/2512.18470)
- *Failure as a Process: An Anatomy of CLI Coding Agent Trajectories*. [arxiv.org/html/2607.09510v1](https://arxiv.org/html/2607.09510v1)
- *What Breaks When LLMs Code?* arXiv:2605.30777. [doi.org/10.48550/arxiv.2605.30777](https://doi.org/10.48550/arxiv.2605.30777)
- *ClayBuddy: … Mitigation of Coding Agent Failures*. [arxiv.org/html/2606.19380](https://arxiv.org/html/2606.19380)
- *Beyond Resolution Rates: Behavioral Drivers of Coding Agent Success and Failure*. arXiv:2604.02547. [arxiv.org/abs/2604.02547](https://arxiv.org/abs/2604.02547)
- *Where Do AI Coding Agents Fail? … Agentic Pull Requests*. [arxiv.org/html/2601.15195v1](https://arxiv.org/html/2601.15195v1)
- Spracklen et al. *We Have a Package for You!* USENIX Security 2025 (package hallucinations).
- *The Range Shrinks, the Threat Remains* (2026 frontier package hallucinations). [arxiv.org/pdf/2605.17062](https://arxiv.org/pdf/2605.17062)

**Industry security**

- Veracode. *Spring 2026 GenAI Code Security Update*. 24 Mar 2026. [veracode.com/blog/spring-2026-genai-code-security](https://www.veracode.com/blog/spring-2026-genai-code-security/)
- Cloud Security Alliance. AI-generated code vulnerability surge, 2026. [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-generated-code-vulnerability-surge-2026/)
- Cloud Security Alliance. Slopsquatting research note, Apr 2026. [labs.cloudsecurityalliance.org](https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419-csa/)
- Endor Labs. *The Most Common Security Vulnerabilities in AI-Generated Code*. [endorlabs.com](https://www.endorlabs.com/learn/the-most-common-security-vulnerabilities-in-ai-generated-code)

**Secondary (conventions / SDD explainers; not treated as papers)**

- DEV: *AGENTS.md vs CLAUDE.md vs .cursorrules* (2026 Cursor read-order). [dev.to/rulestack/...](https://dev.to/rulestack/agentsmd-vs-claudemd-vs-cursorrules-what-cursor-actually-reads-now-and-in-what-order-17bo)
- ProductOS. *What is spec-driven development? (2026)*. [productos.dev](https://productos.dev/blog/spec-driven-development)
- Elasticsearch Labs. *Context engineering vs. prompt engineering*. [elastic.co/search-labs](https://www.elastic.co/search-labs/blog/context-engineering-vs-prompt-engineering)

---

*Document generated for workspace research use, 13 Aug 2026. Update Cursor paths against [cursor.com/docs](https://cursor.com/docs/rules) when the product changes. Do not treat this file as a substitute for reading those docs.*
