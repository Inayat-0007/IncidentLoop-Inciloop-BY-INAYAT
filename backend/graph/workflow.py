from __future__ import annotations

import operator
import time
import uuid
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.agents.decision import decide
from backend.agents.incident import investigate
from backend.agents.knowledge import retrieve_knowledge
from backend.agents.planner import extract_service, plan_steps, resolve_scenario
from backend.agents.release import inspect_release
from backend.agents.verification import verify
from backend.config import use_gemini_for
from backend.errors import GraphRunError, LlmError
from backend.llm import acomplete, stable_ms
from backend.memory import store as memory
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
    traces: Annotated[list[dict[str, Any]], operator.add]
    node_errors: Annotated[list[str], operator.add]
    memory_context: dict[str, Any]


def _trace(agent: str, duration_ms: float, **kwargs: Any) -> dict[str, Any]:
    return AgentTrace(agent=agent, duration_ms=duration_ms, **kwargs).model_dump()


async def planner_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    try:
        prompt = state.get("prompt") or ""
        scenario_id = resolve_scenario(prompt, state.get("scenario_id"))
        service = extract_service(prompt, state.get("service"))
        history = memory.conversation_history(limit=8)
        prev = memory.previous_recommendations(limit=5, service=service, query=prompt)
        similar = memory.similar_incidents(service, prompt, limit=5)
        memory_context = {
            "conversation_history": history,
            "previous_recommendations": [
                {
                    "service": r.get("service"),
                    "recommendation": r.get("recommendation"),
                    "reason": r.get("reason"),
                }
                for r in prev
            ],
            "similar_incidents": similar,
        }
        plan = plan_steps(service, scenario_id)
        if similar:
            plan += " Memory: seen similar incidents " + ", ".join(str(s.get("id")) for s in similar[:3]) + "."
        if use_gemini_for("planner"):
            plan_out = await acomplete(
                "You are the Planner Agent. Output a short numbered plan. Never execute rollback. "
                "Use conversation history and prior recommendations as context only.",
                plan + "\ncontext=" + str(memory_context),
            )
        else:
            plan_out = plan
        status = "ok"
        errors: list[str] = []
    except (LlmError, GraphRunError):
        raise
    except Exception as exc:
        raise GraphRunError(502, "planner_failed", f"Planner failed ({type(exc).__name__})") from exc
    traces = [
        _trace(
            "planner",
            (time.perf_counter() - t0) * 1000 or stable_ms("planner"),
            tools_used=[],
            status=status,
        )
    ]
    return {
        "incident_id": state.get("incident_id") or f"inc_{uuid.uuid4().hex[:10]}",
        "scenario_id": scenario_id,
        "service": service,
        "plan": plan_out,
        "traces": traces,
        "node_errors": errors,
        "memory_context": memory_context,
    }


async def incident_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    try:
        result = await investigate(state["scenario_id"], state["service"])
    except (LlmError, GraphRunError):
        raise
    except Exception as exc:
        raise GraphRunError(502, "tool_upstream", f"Incident tools failed ({type(exc).__name__})") from exc
    return {
        "metrics": result["metrics"],
        "logs": result["logs"],
        "traces": [
            _trace(
                "incident",
                (time.perf_counter() - t0) * 1000,
                tools_used=result["tools"],
                status="ok",
            )
        ],
    }


async def knowledge_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    try:
        query = (
            f"{state.get('prompt')} {state.get('service')} checkout 500 deploy database timeout rollback policy"
        )
        result = await retrieve_knowledge(query, state.get("service") or "")
    except (LlmError, GraphRunError):
        raise
    except Exception as exc:
        raise GraphRunError(502, "knowledge_failed", f"Knowledge retrieve failed ({type(exc).__name__})") from exc
    return {
        "docs": result["docs"],
        "doc_ids": result["ids"],
        "traces": [
            _trace(
                "knowledge",
                (time.perf_counter() - t0) * 1000,
                tools_used=result["tools"],
                docs_retrieved=result["ids"]
                + [str(h.get("id")) for h in (result.get("memory_hits") or [])],
                status="ok",
            )
        ],
    }


async def release_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    try:
        result = await inspect_release(state["scenario_id"])
    except (LlmError, GraphRunError):
        raise
    except Exception as exc:
        raise GraphRunError(502, "tool_upstream", f"Release tool failed ({type(exc).__name__})") from exc
    return {
        "release": result["release"],
        "traces": [
            _trace(
                "release",
                (time.perf_counter() - t0) * 1000,
                tools_used=result["tools"],
                status="ok",
            )
        ],
    }


async def decision_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    try:
        decision: Decision = await decide(
            prompt=state.get("prompt") or "",
            service=state.get("service") or "",
            scenario_id=state.get("scenario_id") or "default",
            metrics=state.get("metrics") or {},
            logs=state.get("logs") or {},
            release=state.get("release") or {},
            docs=state.get("docs") or [],
            memory_context=state.get("memory_context") or {},
        )
    except (LlmError, GraphRunError):
        raise
    except Exception as exc:
        raise GraphRunError(502, "decision_failed", f"Decision failed ({type(exc).__name__})") from exc
    return {
        "decision": decision.model_dump(),
        "traces": [
            _trace(
                "decision",
                (time.perf_counter() - t0) * 1000,
                tools_used=[],
                recommendation=decision.recommendation.value,
                confidence=decision.confidence,
                status="ok",
            )
        ],
    }


async def verification_node(state: GraphState) -> GraphState:
    t0 = time.perf_counter()
    try:
        decision = Decision.model_validate(state["decision"])
        result = await verify(state["scenario_id"], state["service"], decision)
    except (LlmError, GraphRunError):
        raise
    except Exception as exc:
        raise GraphRunError(502, "verification_failed", f"Verification failed ({type(exc).__name__})") from exc
    return {
        "verification": result,
        "traces": [
            _trace(
                "verification",
                (time.perf_counter() - t0) * 1000,
                tools_used=result["tools"],
                recommendation=decision.recommendation.value,
                confidence=decision.confidence,
                status=result["status"],
            )
        ],
    }


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("planner", planner_node)
    g.add_node("incident", incident_node)
    g.add_node("knowledge", knowledge_node)
    g.add_node("release", release_node)
    g.add_node("decision", decision_node)
    g.add_node("verification", verification_node)
    g.add_edge(START, "planner")
    # Independent tool/RAG work runs concurrently after plan.
    g.add_edge("planner", "incident")
    g.add_edge("planner", "knowledge")
    g.add_edge("planner", "release")
    g.add_edge("incident", "decision")
    g.add_edge("knowledge", "decision")
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


async def run_investigation(prompt: str, scenario_id: str | None = None, service: str | None = None) -> GraphState:
    app = get_app()
    initial: GraphState = {
        "prompt": prompt,
        "traces": [],
        "node_errors": [],
    }
    if scenario_id:
        initial["scenario_id"] = scenario_id
    if service:
        initial["service"] = service
    return await app.ainvoke(initial)
