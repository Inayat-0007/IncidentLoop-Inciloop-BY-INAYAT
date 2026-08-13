from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Recommendation(StrEnum):
    ROLLBACK = "ROLLBACK"
    INVESTIGATE = "INVESTIGATE"
    NO_ACTION = "NO_ACTION"
    ESCALATE = "ESCALATE"


class Decision(BaseModel):
    service: str
    observed_metrics: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    recommendation: Recommendation
    reason: str
    confidence: float = Field(ge=0, le=1)


class InvestigateRequest(BaseModel):
    prompt: str
    scenario_id: str | None = None
    service: str | None = None


class RollbackRequest(BaseModel):
    authorized: bool
    scenario_id: str | None = None


class MockRollbackRequest(BaseModel):
    scenario_id: str | None = None
    authorized: bool = False


class AgentTrace(BaseModel):
    agent: str
    duration_ms: float
    tools_used: list[str] = Field(default_factory=list)
    docs_retrieved: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    confidence: float | None = None
    status: str = "ok"


class IncidentRecord(BaseModel):
    id: str
    prompt: str
    scenario_id: str
    service: str
    status: str
    decision: Decision
    verification: dict[str, Any] = Field(default_factory=dict)
    traces: list[AgentTrace] = Field(default_factory=list)
    release: dict[str, Any] = Field(default_factory=dict)
    logs: list[str] = Field(default_factory=list)


class ErrorBody(BaseModel):
    error: str
    code: str
    detail: str
    message: str
