# Company telemetry (exported files)

Drop three snapshots here. Restart the API (ingest is on startup for `knowledge/`; telemetry is read on each request).

| File | Shape |
|---|---|
| `metrics.json` | `{ "service", "error_rate", "latency_ms", "status" }` or Prometheus `{ "data": { "result": [...] } }` |
| `logs.jsonl` or `logs.json` | JSONL lines, `["line"]`, or `{ "lines": [] }` |
| `releases.json` | `{ "version", "deployed_at", "previous_version", "rollback_available" }` |

Copy `templates/` then overwrite with Grafana/Prometheus export, a log download, and a changelog. **Do not commit real logs that look like PII.**

If these live files are missing, DevOpsPilot loads `sample/` and sets `data_mode: sample_bundle`.

**Rollback:** recommendation is not execution. With `DATA_SOURCE=files` and no `ROLLBACK_WEBHOOK_URL`, an authorized execute only appends `rollback_events.json` and may set `desired_version` in `releases.json`. That is not Kubernetes. To actually roll a deploy, set `ROLLBACK_WEBHOOK_URL` to your CD hook.

**Runbooks:** replace or add markdown under `knowledge/` and restart so ingest picks them up.
