# Data model — DevOpsPilot

No Postgres in MVP. Persistence is local files under `data/` (gitignored except README, company sample/templates).

Company telemetry (not committed live dumps): `data/company/metrics.json`, `logs.jsonl` or `logs.json`, `releases.json`. Sample bundle: `data/company/sample/`. Rollback audit: `data/company/rollback_events.json`.

## Incident

| Field | Type | Notes |
|---|---|---|
| id | string | `inc_` + uuid |
| prompt | string | User text |
| scenario_id | string | Sim scenario |
| service | string | e.g. `checkout-api` |
| status | enum | `investigating` `recommended` `executed` `verified` `rejected` |
| decision | Decision | Pydantic snapshot |
| created_at | iso8601 | |

## Decision (API + memory)

| Field | Type |
|---|---|
| service | string |
| observed_metrics | object (error_rate, latency_ms, status) |
| evidence | string[] |
| recommendation | `ROLLBACK` `INVESTIGATE` `NO_ACTION` `ESCALATE` |
| reason | string |
| confidence | float 0–1 |

## AgentOps trace

| Field | Type |
|---|---|
| incident_id | string |
| agent | string |
| duration_ms | number |
| tools_used | string[] |
| docs_retrieved | string[] |
| recommendation | string? |
| confidence | number? |
| status | string |

## Memory tables (SQLite)

- `conversations` (incident_id, role, content, ts)
- `incidents` (id, json payload)
- `recommendations` (incident_id, json, ts)
- `resolved` (incident_id, ts)

## Sim production

In-memory (process) keyed by `scenario_id`. Rollback mutates metrics to healthy for that scenario instance.
