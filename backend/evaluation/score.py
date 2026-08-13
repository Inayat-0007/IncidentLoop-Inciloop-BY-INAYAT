from __future__ import annotations

from dataclasses import dataclass, field

from backend.evaluation.test_cases import EvalCase

EXPECTED_TOOLS = (
    "GET /api/metrics",
    "GET /api/logs",
    "rag.retrieve",
    "GET /api/releases/latest",
)

WILD_LATENCY_MS = 120_000.0


@dataclass
class CaseScore:
    case_id: str
    decision_ok: bool
    tools_ok: bool
    rag_ok: bool
    latency_ms: float


@dataclass
class EvalReport:
    n: int
    decision_accuracy: float
    tool_call_correctness: float
    rag_relevance: float
    latency_ms: list[float] = field(default_factory=list)
    cases: list[CaseScore] = field(default_factory=list)

    def as_text(self) -> str:
        p50 = sorted(self.latency_ms)[len(self.latency_ms) // 2] if self.latency_ms else 0.0
        return (
            f"eval n={self.n} decision_accuracy={self.decision_accuracy:.1f}% "
            f"tool_call_correctness={self.tool_call_correctness:.1f}% "
            f"rag_relevance={self.rag_relevance:.1f}% "
            f"latency_p50_ms={p50:.0f} max_ms={max(self.latency_ms, default=0):.0f}"
        )


def rag_keywords_for(case: EvalCase) -> tuple[str, ...]:
    prompt = (case.prompt or "").lower()
    if "checkout" in prompt and (
        "500" in prompt or "deploy" in prompt or "timeout" in prompt or "db" in prompt
    ):
        return (
            "checkout-500-runbook",
            "deployment-rollback-policy",
            "database-timeout",
            "rollback",
        )
    return ()


def _tools_from_body(body: dict) -> set[str]:
    traces = body.get("traces") or []
    used: set[str] = set()
    for t in traces:
        used.update(t.get("tools_used") or [])
    return used


def _docs_blob(body: dict) -> str:
    traces = body.get("traces") or []
    parts: list[str] = []
    for t in traces:
        parts.extend(t.get("docs_retrieved") or [])
    evidence = (body.get("decision") or {}).get("evidence") or []
    parts.extend(str(e) for e in evidence)
    return " ".join(parts).lower()


def score_case(case: EvalCase, body: dict, latency_ms: float) -> CaseScore:
    rec = (body.get("decision") or {}).get("recommendation")
    decision_ok = rec == case.expected.value
    tools = _tools_from_body(body)
    tools_ok = all(t in tools for t in EXPECTED_TOOLS)
    keywords = rag_keywords_for(case)
    blob = _docs_blob(body)
    if keywords:
        rag_ok = any(k.lower() in blob for k in keywords)
    else:
        rag_ok = True
    return CaseScore(
        case_id=case.id,
        decision_ok=decision_ok,
        tools_ok=tools_ok,
        rag_ok=rag_ok,
        latency_ms=latency_ms,
    )


def score_results(rows: list[CaseScore]) -> EvalReport:
    n = len(rows) or 1
    return EvalReport(
        n=len(rows),
        decision_accuracy=100.0 * sum(1 for r in rows if r.decision_ok) / n,
        tool_call_correctness=100.0 * sum(1 for r in rows if r.tools_ok) / n,
        rag_relevance=100.0 * sum(1 for r in rows if r.rag_ok) / n,
        latency_ms=[r.latency_ms for r in rows],
        cases=rows,
    )


def latency_wildly_broken(report: EvalReport) -> bool:
    return any(ms > WILD_LATENCY_MS for ms in report.latency_ms)


__all__ = [
    "EXPECTED_TOOLS",
    "EvalReport",
    "latency_wildly_broken",
    "score_case",
    "score_results",
]
