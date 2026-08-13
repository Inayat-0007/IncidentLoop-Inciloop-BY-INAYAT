import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ApiErrorBody, Incident, OpsTraces, Trace } from "./types";

const FLOW = ["PLAN", "INVESTIGATE", "RETRIEVE", "ACT", "VERIFY"] as const;

const AGENT_LABELS: Record<string, string> = {
  planner: "Planner",
  incident: "Incident Agent",
  knowledge: "Knowledge",
  release: "Release",
  decision: "Decision",
  verification: "Verification",
};

const AGENT_STAGE: Record<string, (typeof FLOW)[number]> = {
  planner: "PLAN",
  incident: "INVESTIGATE",
  knowledge: "RETRIEVE",
  release: "ACT",
  decision: "ACT",
  verification: "VERIFY",
};

const QUOTES = [
  "Prefer evidence over intuition.",
  "Recommendation is not execution.",
  "Rollback stays behind a human gate.",
  "If Gemini is down, we fail closed.",
  "Company files in, recommendation out. No auto-rollback.",
];

const DEFAULT_PROMPT =
  "web-api is returning 500 after the latest deploy; postgres primary unreadable and connection refused";

const STAGGER_MS = 220;

function fmtMs(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}

function parseApiError(status: number, body: ApiErrorBody | null, fallback: string): string {
  const detail = body?.detail || body?.message || body?.error;
  const code = body?.code;
  const head =
    status === 502 || status === 503
      ? `Gemini unavailable (${status})`
      : `Request failed (${status})`;
  if (detail && code) return `${head}: ${code} — ${detail}`;
  if (detail) return `${head}: ${detail}`;
  return `${head}: ${fallback}`;
}

function recClass(rec: string): string {
  if (rec === "ROLLBACK") return "rollback";
  if (rec === "ESCALATE") return "escalate";
  if (rec === "INVESTIGATE") return "investigate";
  if (rec === "NO_ACTION") return "idle";
  return "";
}

function renderTraceLines(traces: Trace[]): string {
  if (!traces.length) {
    return "│ (run Investigate to populate traces)                   │\n";
  }
  return traces
    .map((t) => {
      const name = (AGENT_LABELS[t.agent] ?? t.agent).padEnd(16);
      const dur = fmtMs(t.duration_ms).padEnd(7);
      const extra = [
        t.tools_used?.length ? `tools: ${t.tools_used.join(",")}` : "",
        t.docs_retrieved?.length ? `docs: ${t.docs_retrieved.join(",")}` : "",
      ]
        .filter(Boolean)
        .join("  ");
      const line = `│ ${name} ${dur} ${extra}`;
      return line.slice(0, 59).padEnd(59) + "│\n";
    })
    .join("");
}

export default function App() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [token, setToken] = useState("replace_me_with_a_local_token");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [ops, setOps] = useState<OpsTraces | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [busyKind, setBusyKind] = useState<"idle" | "investigate" | "rollback">("idle");
  const [visibleTraces, setVisibleTraces] = useState(0);
  const [quoteIx, setQuoteIx] = useState(0);
  const [health, setHealth] = useState<"unknown" | "ok" | "down">("unknown");
  const [dataBadge, setDataBadge] = useState("Company files");
  const [dataMode, setDataMode] = useState<string | null>(null);
  const [submittedPrompt, setSubmittedPrompt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function ping() {
      try {
        const r = await fetch("/health");
        const body = await r.json().catch(() => null);
        if (!cancelled) {
          setHealth(r.ok && body?.status === "ok" ? "ok" : "down");
          if (body?.badge) setDataBadge(String(body.badge));
          if (body?.data_mode) setDataMode(String(body.data_mode));
        }
      } catch {
        if (!cancelled) setHealth("down");
      }
    }
    ping();
    const id = window.setInterval(ping, 20000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!busy) return;
    const id = window.setInterval(() => {
      setQuoteIx((i) => (i + 1) % QUOTES.length);
    }, 2400);
    return () => window.clearInterval(id);
  }, [busy]);

  useEffect(() => {
    if (!incident) {
      setVisibleTraces(0);
      return;
    }
    setVisibleTraces(0);
    const n = incident.traces.length;
    if (!n) return;
    const timers: number[] = [];
    for (let i = 1; i <= n; i += 1) {
      timers.push(window.setTimeout(() => setVisibleTraces(i), i * STAGGER_MS));
    }
    return () => {
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [incident]);

  const traces = incident?.traces ?? [];
  const shown = traces.slice(0, visibleTraces);
  const runtime = useMemo(() => {
    if (ops?.runtime_ms != null) return ops.runtime_ms;
    if (!incident) return 0;
    return incident.traces.reduce((a, t) => a + (t.duration_ms || 0), 0);
  }, [incident, ops]);

  const rec = incident?.decision.recommendation ?? "—";
  const conf = incident ? `${Math.round(incident.decision.confidence * 100)}%` : "—";
  const canRollback = Boolean(incident?.id) && rec === "ROLLBACK" && !busy;

  const litStages = new Set(shown.map((t) => AGENT_STAGE[t.agent]).filter(Boolean));
  const nextAgent = traces[visibleTraces]?.agent;
  const activeStage = busy && busyKind === "investigate" ? FLOW[Math.min(quoteIx, FLOW.length - 1)] : AGENT_STAGE[nextAgent ?? ""];

  async function loadOps(id: string) {
    try {
      const r = await fetch(`/ops/${id}`);
      if (!r.ok) return;
      const body = (await r.json()) as OpsTraces;
      setOps(body);
    } catch {
      /* traces from POST /investigate remain authoritative */
    }
  }

  async function onInvestigate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setBusyKind("investigate");
    setError(null);
    setIncident(null);
    setOps(null);
    setSubmittedPrompt(prompt);
    try {
      const r = await fetch("/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const body = await r.json().catch(() => null);
      if (!r.ok) {
        throw new Error(parseApiError(r.status, body, r.statusText));
      }
      const recvd = body as Incident;
      setIncident(recvd);
      await loadOps(recvd.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "investigate failed");
    } finally {
      setBusy(false);
      setBusyKind("idle");
    }
  }

  async function onRollback() {
    if (!incident) return;
    setBusy(true);
    setBusyKind("rollback");
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
      const body = await r.json().catch(() => null);
      if (!r.ok) throw new Error(parseApiError(r.status, body, r.statusText));
      setIncident(body as Incident);
      await loadOps(incident.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "rollback failed");
    } finally {
      setBusy(false);
      setBusyKind("idle");
    }
  }

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            DP
          </div>
          <h1>DevOpsPilot</h1>
          <p className="lede">Incident war-room assistant. Investigate, retrieve runbooks, recommend — never auto-rollback.</p>
        </div>
        <div className="badge-row">
          <span className="badge">{dataBadge} · real Gemini</span>
          {dataMode === "sample_bundle" ? (
            <span className="badge warn">sample_bundle — drop files in data/company/</span>
          ) : dataMode ? (
            <span className="badge">data_mode: {dataMode}</span>
          ) : null}
        </div>
        <div className="health" aria-live="polite">
          <span className={`dot ${health === "ok" ? "ok" : health === "down" ? "down" : ""}`} />
          API {health === "ok" ? "healthy" : health === "down" ? "unreachable" : "checking…"}
        </div>
        <ol className="flow" aria-label="Investigation pipeline">
          {FLOW.map((step) => {
            const done = litStages.has(step) && activeStage !== step;
            const active = activeStage === step && (busy || visibleTraces < traces.length);
            return (
              <li key={step} className={done ? "done" : active ? "active" : litStages.has(step) ? "done" : ""}>
                {step}
              </li>
            );
          })}
        </ol>
      </aside>

      <main className="canvas">
        <div className="thread" aria-busy={busy}>
          {!submittedPrompt && !incident ? (
            <section className="msg">
              <div className="who">Briefing</div>
              <div className="bubble">
                <p>
                  Describe a symptom from your exported metrics/logs/releases (or the sample bundle). The graph
                  runs PLAN → INVESTIGATE → RETRIEVE → ACT → VERIFY. Execution still requires your token and
                  does not auto-rollback production.
                </p>
              </div>
            </section>
          ) : null}

          {submittedPrompt ? (
            <section className="msg user">
              <div className="who">On-call</div>
              <div className="bubble">
                <p>{submittedPrompt}</p>
              </div>
            </section>
          ) : null}

          {busy && busyKind === "investigate" ? (
            <div className="waiting" aria-live="polite">
              <p className="quote">{QUOTES[quoteIx]}</p>
              <div className="skel" />
              <div className="skel" />
              <div className="skel" />
            </div>
          ) : null}

          {incident ? (
            <section className="msg">
              <div className="who">Assistant</div>
              <div className="verdict">
                <span className={`rec ${recClass(rec)}`}>{rec}</span>
                <span className="meta">
                  confidence {conf} · {incident.service} · {incident.status}
                </span>
              </div>
              <p className="reason">{incident.decision.reason}</p>
              <div className="traces">
                {shown.map((t, i) => (
                  <article className="trace" key={`${t.agent}-${i}`} style={{ animationDelay: `${i * 40}ms` }}>
                    <div className="trace-head">
                      <span className="agent">{AGENT_LABELS[t.agent] ?? t.agent}</span>
                      <span className="dur">{fmtMs(t.duration_ms)}</span>
                    </div>
                    <div className="chips">
                      {(t.tools_used ?? []).map((tool) => (
                        <span className="chip" key={tool}>
                          {tool}
                        </span>
                      ))}
                      {(t.docs_retrieved ?? []).map((doc) => (
                        <span className="chip" key={doc}>
                          {doc}
                        </span>
                      ))}
                      {t.status ? <span className="chip">{t.status}</span> : null}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          <details className="raw">
            <summary>Raw AgentOps (ASCII)</summary>
            <pre className="ascii" aria-label="AgentOps dashboard">
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
          </details>
        </div>

        <form className="composer" onSubmit={onInvestigate}>
          <div className="composer-inner">
            <label htmlFor="prompt">Incident prompt</label>
            <textarea
              id="prompt"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              disabled={busy}
            />
            <label htmlFor="token">Rollback token</label>
            <input
              id="token"
              type="password"
              autoComplete="off"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={busy}
            />
            <div className="actions">
              <button className="primary" type="submit" disabled={busy}>
                {busy && busyKind === "investigate" ? "Investigating…" : "Investigate"}
              </button>
              <button className="danger" type="button" disabled={!canRollback} onClick={onRollback}>
                {busy && busyKind === "rollback" ? "Authorizing…" : "Authorize rollback"}
              </button>
            </div>
            {error ? (
              <p className="err" role="alert">
                {error}
              </p>
            ) : null}
          </div>
        </form>
      </main>

      <aside className="artifact" aria-label="Evidence">
        <h2>Artifact</h2>
        {incident ? (
          <>
            <div className="kv">
              <div>
                <span className="k">Incident</span>
                <span className="v">{incident.id}</span>
              </div>
              <div>
                <span className="k">Scenario</span>
                <span className="v">{incident.scenario_id}</span>
              </div>
              <div>
                <span className="k">Runtime</span>
                <span className="v">{fmtMs(runtime)}</span>
              </div>
              <div>
                <span className="k">Recommendation</span>
                <span className="v">{rec}</span>
              </div>
            </div>
            <h2>Evidence</h2>
            <ul className="evidence">
              {incident.decision.evidence.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            {incident.verification && Object.keys(incident.verification).length ? (
              <>
                <h2>Verification</h2>
                <p className="empty-art">
                  {String(
                    (incident.verification as { note?: string; status?: string }).note ||
                      (incident.verification as { status?: string }).status ||
                      "Recorded after authorized rollback.",
                  )}
                </p>
              </>
            ) : null}
          </>
        ) : (
          <p className="empty-art">Evidence, confidence, and tool names land here after Investigate returns. Nothing is invented while Gemini is thinking.</p>
        )}
      </aside>
    </div>
  );
}
