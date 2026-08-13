import { FormEvent, useMemo, useState } from "react";
import type { Incident, Trace } from "./types";

const DEFAULT_PROMPT =
  "checkout-api is throwing 500 after the latest deploy; PaymentService timeout and DB connection refused";

function fmtMs(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}

export default function App() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [token, setToken] = useState("replace_me_with_a_local_token");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const runtime = useMemo(() => {
    if (!incident) return 0;
    return incident.traces.reduce((a, t) => a + (t.duration_ms || 0), 0);
  }, [incident]);

  async function onInvestigate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const body = await r.json().catch(() => null);
      if (!r.ok) {
        const msg =
          (body && (body.detail || body.message || body.error)) || r.statusText;
        throw new Error(String(msg));
      }
      setIncident(body as Incident);
    } catch (err) {
      setError(err instanceof Error ? err.message : "investigate failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRollback() {
    if (!incident) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/incidents/${incident.id}/rollback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ authorized: true, scenario_id: incident.scenario_id }),
      });
      const body = await r.json();
      if (!r.ok) throw new Error(body.message || r.statusText);
      setIncident(body as Incident);
    } catch (err) {
      setError(err instanceof Error ? err.message : "rollback failed");
    } finally {
      setBusy(false);
    }
  }

  const rec = incident?.decision.recommendation ?? "—";
  const conf = incident ? `${Math.round(incident.decision.confidence * 100)}%` : "—";

  return (
    <main>
      <h1>DevOpsPilot AgentOps</h1>
      <p className="pitch">PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY (simulated production)</p>

      <form onSubmit={onInvestigate}>
        <label htmlFor="prompt">Incident prompt</label>
        <textarea id="prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={3} />
        <label htmlFor="token">Rollback token (never committed)</label>
        <input
          id="token"
          type="password"
          autoComplete="off"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <div className="row">
          <button type="submit" disabled={busy}>
            Investigate
          </button>
          <button
            type="button"
            disabled={busy || !incident || rec !== "ROLLBACK"}
            onClick={onRollback}
          >
            Authorize rollback
          </button>
        </div>
      </form>

      {error ? <p className="err" role="alert">{error}</p> : null}

      <section className="panel" aria-label="AgentOps dashboard">
        <pre className="ascii">
{`┌──────────────────────────────────────────────────────────┐
│ AgentOps Dashboard                                       │
│ Incident: ${(incident?.id ?? "—").padEnd(43)}│
│ Service:  ${(incident?.service ?? "—").padEnd(43)}│
│                                                          │
${renderTraceLines(incident?.traces ?? [])}│ Runtime: ${fmtMs(runtime).padEnd(45)}│
│ Recommendation: ${rec.padEnd(39)}│
│ Confidence: ${conf.padEnd(43)}│
│ Status: ${(incident?.status ?? "idle").padEnd(47)}│
└──────────────────────────────────────────────────────────┘`}
        </pre>
      </section>

      {incident ? (
        <section>
          <h2>Evidence</h2>
          <ul>
            {incident.decision.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p>
            <strong>Reason:</strong> {incident.decision.reason}
          </p>
        </section>
      ) : null}
    </main>
  );
}

function renderTraceLines(traces: Trace[]): string {
  const labels: Record<string, string> = {
    planner: "Planner",
    incident: "Incident Agent",
    knowledge: "Knowledge",
    release: "Release",
    decision: "Decision",
    verification: "Verification",
  };
  if (!traces.length) {
    return "│ (run Investigate to populate traces)                   │\n";
  }
  return traces
    .map((t) => {
      const name = (labels[t.agent] ?? t.agent).padEnd(16);
      const dur = fmtMs(t.duration_ms).padEnd(7);
      const extra = [
        t.tools_used.length ? `tools: ${t.tools_used.join(",")}` : "",
        t.docs_retrieved.length ? `docs: ${t.docs_retrieved.join(",")}` : "",
      ]
        .filter(Boolean)
        .join("  ");
      const line = `│ ${name} ${dur} ${extra}`;
      return line.slice(0, 59).padEnd(59) + "│\n";
    })
    .join("");
}
