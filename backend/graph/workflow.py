from __future__ import annotations

import time
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.decision import decide
from backend.agents.incident import investigate
from backend.agents.knowledge import retrieve_knowledge
from backend.agents.planner import extract_service, plan_steps, resolve_scenario
from backend.agents.release import inspect_release
from backend.agents.verification import verify
from backend.llm import complete, stable_ms
from backend.schemas import AgentTrace, Decision


class GraphState(TypedDict, total=False):
    incident_id: str
    prompt: str
    scenario_id: str
    service: str
    plan: str
    metrics: dict[str, Any]
    logs: dict[str, Any]
    docs: list[dict[str, str]]
    doc_ids: list[str]
    release: dict[str, Any]
    decision: dict[str, Any]
    verification: dict[str, Any]
    traces: list[dict[str, Any]]


def _trace(agent: str, duration_ms: float, **kwargs: Any) -> dict[str, Any]:
    return AgentTrace(agent=agent, duration_ms=duration_ms, **kwargs).model_dump()


def planner_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    prompt = state.get("prompt") or ""
    scenario_id = resolve_scenario(prompt, state.get("scenario_id"))
    service = extract_service(prompt, state.get("service"))
    plan = plan_steps(service, scenario_id)
    llm = complete("You are the Planner Agent. Output a short numbered plan. Never execute rollback.", plan)
    traces = list(state.get("traces") or [])
    traces.append(
        _trace(
            "planner",
            (time.perf_counter() - t0) * 1000 or stable_ms("planner"),
            tools_used=[],
            status="ok",
        )
    )
    return {
        **state,
        "incident_id": state.get("incident_id") or f"inc_{uuid.uuid4().hex[:10]}",
        "scenario_id": scenario_id,
        "service": service,
        "plan": llm or plan,
        "traces": traces,
    }


def incident_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    result = investigate(state["scenario_id"], state["service"])
    traces = list(state.get("traces") or [])
    traces.append(
        _trace(
            "incident",
            (time.perf_counter() - t0) * 1000,
            tools_used=result["tools"],
            status="ok",
        )
    )
    return {**state, "metrics": result["metrics"], "logs": result["logs"], "traces": traces}


def knowledge_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    query = (
        f"{state.get('prompt')} {state.get('service')} checkout 500 deploy database timeout rollback policy"
    )
    result = retrieve_knowledge(query)
    traces = list(state.get("traces") or [])
    traces.append(
        _trace(
            "knowledge",
            (time.perf_counter() - t0) * 1000,
            tools_used=result["tools"],
            docs_retrieved=result["ids"],
            status="ok",
        )
    )
    return {**state, "docs": result["docs"], "doc_ids": result["ids"], "traces": traces}


def release_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    result = inspect_release(state["scenario_id"])
    traces = list(state.get("traces") or [])
    traces.append(
        _trace(
            "release",
            (time.perf_counter() - t0) * 1000,
            tools_used=result["tools"],
            status="ok",
        )
    )
    return {**state, "release": result["release"], "traces": traces}


def decision_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    decision: Decision = decide(
        prompt=state.get("prompt") or "",
        service=state.get("service") or "",
        scenario_id=state.get("scenario_id") or "default",
        metrics=state.get("metrics") or {},
        logs=state.get("logs") or {},
        release=state.get("release") or {},
        docs=state.get("docs") or [],
    )
    traces = list(state.get("traces") or [])
    traces.append(
        _trace(
            "decision",
            (time.perf_counter() - t0) * 1000,
            tools_used=[],
            recommendation=decision.recommendation.value,
            confidence=decision.confidence,
            status="ok",
        )
    )
    return {**state, "decision": decision.model_dump(), "traces": traces}


def verification_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    decision = Decision.model_validate(state["decision"])
    result = verify(state["scenario_id"], state["service"], decision)
    traces = list(state.get("traces") or [])
    traces.append(
        _trace(
            "verification",
            (time.perf_counter() - t0) * 1000,
            tools_used=result["tools"],
            recommendation=decision.recommendation.value,
            confidence=decision.confidence,
            status=result["status"],
        )
    )
    return {**state, "verification": result, "traces": traces}


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("planner", planner_node)
    g.add_node("incident", incident_node)
    g.add_node("knowledge", knowledge_node)
    g.add_node("release", release_node)
    g.add_node("decision", decision_node)
    g.add_node("verification", verification_node)
    g.add_edge(START, "planner")
    g.add_edge("planner", "incident")
    g.add_edge("incident", "knowledge")
    g.add_edge("knowledge", "release")
    g.add_edge("release", "decision")
    g.add_edge("decision", "verification")
    g.add_edge("verification", END)
    return g.compile()


_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = build_graph()
    return _APP


def run_investigation(prompt: str, scenario_id: str | None = None, service: str | None = None) -> GraphState:
    app = get_app()
    initial: GraphState = {
        "prompt": prompt,
        "traces": [],
    }
    if scenario_id:
        initial["scenario_id"] = scenario_id
    if service:
        initial["service"] = service
    return app.invoke(initial)
