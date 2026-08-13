from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import os
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.config import GEMINI_TIMEOUT_S, heuristic_enabled
from backend.errors import LlmError


def _require_gemini_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or ""
    if not key.strip():
        raise LlmError(
            503,
            "llm_unavailable",
            "GEMINI_API_KEY is not set. Live investigate requires real Gemini. "
            "DEVOPSPILOT_FORCE_HEURISTIC is test-only (pytest/CI).",
        )
    return key


def _build_gemini() -> Any:
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=_require_gemini_key(),
    )


class GeminiDecisionOut(BaseModel):
    recommendation: Literal["ROLLBACK", "INVESTIGATE", "NO_ACTION", "ESCALATE"]
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)


def _map_gemini_exc(exc: BaseException) -> LlmError:
    if isinstance(exc, TimeoutError):
        return LlmError(503, "llm_timeout", "Gemini timed out")
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in {401, 403}:
        return LlmError(502, "llm_upstream", "Gemini rejected the request")
    if status == 404:
        return LlmError(502, "llm_upstream", "Gemini model not found (check GEMINI_MODEL)")
    if status == 429:
        return LlmError(503, "llm_quota", "Gemini quota or rate limit")
    return LlmError(502, "llm_upstream", f"Gemini request failed ({type(exc).__name__})")


async def acomplete(system: str, user: str) -> str:
    """Real Gemini completion. Raises LlmError — never returns heuristic text."""
    if heuristic_enabled():
        raise LlmError(
            503,
            "llm_unavailable",
            "Heuristic mode is on; Gemini is not called.",
        )
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception as exc:
        raise LlmError(503, "llm_unavailable", "LangChain is not available") from exc

    try:
        llm = _build_gemini()
    except LlmError:
        raise
    except Exception as exc:
        raise LlmError(502, "llm_upstream", f"Gemini client init failed ({type(exc).__name__})") from exc

    try:
        msg = await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)]),
            timeout=GEMINI_TIMEOUT_S,
        )
    except TimeoutError as exc:
        raise _map_gemini_exc(exc) from exc
    except LlmError:
        raise
    except Exception as exc:
        raise _map_gemini_exc(exc) from exc

    content = getattr(msg, "content", None)
    text = str(content).strip() if content else ""
    if not text:
        raise LlmError(502, "llm_invalid_output", "Gemini returned an empty completion")
    return text


async def acomplete_decision(system: str, user: str) -> GeminiDecisionOut:
    """Gemini structured decision. No heuristic fill-in."""
    if heuristic_enabled():
        raise LlmError(503, "llm_unavailable", "Heuristic mode is on; Gemini is not called.")
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception as exc:
        raise LlmError(503, "llm_unavailable", "LangChain is not available") from exc
    try:
        llm = _build_gemini()
        structured = llm.with_structured_output(GeminiDecisionOut, method="json_schema")
        raw = await asyncio.wait_for(
            structured.ainvoke([SystemMessage(content=system), HumanMessage(content=user)]),
            timeout=GEMINI_TIMEOUT_S,
        )
        if isinstance(raw, GeminiDecisionOut):
            return raw
        if isinstance(raw, dict):
            return GeminiDecisionOut.model_validate(raw)
    except LlmError:
        raise
    except TimeoutError as exc:
        raise _map_gemini_exc(exc) from exc
    except Exception as exc:
        mapped = _map_gemini_exc(exc)
        if mapped.code in {"llm_quota", "llm_timeout"}:
            raise mapped from exc
    text = await acomplete(system, user)
    data = parse_json_object(text)
    try:
        return GeminiDecisionOut.model_validate(data)
    except Exception as exc:
        raise LlmError(502, "llm_invalid_output", "Gemini decision was not valid JSON") from exc


def _repair_jsonish(blob: str) -> str:
    blob = blob.replace("True", "true").replace("False", "false").replace("None", "null")
    return re.sub(r",\s*([}\]])", r"\1", blob)


def parse_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise LlmError(502, "llm_invalid_output", "Gemini did not return JSON")
        blob = raw[start : end + 1]
        data: Any = None
        for candidate in (blob, _repair_jsonish(blob)):
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                try:
                    parsed = ast.literal_eval(candidate)
                except (SyntaxError, ValueError):
                    continue
                if isinstance(parsed, dict):
                    data = parsed
                    break
        if not isinstance(data, dict):
            raise LlmError(502, "llm_invalid_output", "Gemini JSON could not be parsed")
    if not isinstance(data, dict):
        raise LlmError(502, "llm_invalid_output", "Gemini JSON was not an object")
    return data


def stable_ms(seed: str, base: int = 80) -> float:
    n = int(hashlib.sha256(seed.encode()).hexdigest()[:4], 16)
    return float(base + (n % 40))
