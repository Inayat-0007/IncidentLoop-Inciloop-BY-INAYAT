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


def _model_chain() -> list[str]:
    primary = (os.getenv("GEMINI_MODEL") or "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    extras = [
        p.strip()
        for p in (os.getenv("GEMINI_MODEL_FALLBACK") or "").split(",")
        if p.strip()
    ]
    out: list[str] = []
    seen: set[str] = set()
    for name in [primary, *extras]:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _build_gemini(model: str) -> Any:
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=_require_gemini_key(),
    )


class GeminiDecisionOut(BaseModel):
    recommendation: Literal["ROLLBACK", "INVESTIGATE", "NO_ACTION", "ESCALATE"]
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)


def _exc_blob(exc: BaseException) -> str:
    parts: list[str] = []
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        parts.append(type(cur).__name__)
        parts.append(str(cur))
        cur = cur.__cause__ or cur.__context__
    return " ".join(parts).lower()


def _http_status(exc: BaseException) -> int | None:
    cur: BaseException | None = exc
    seen: set[int] = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        for attr in ("status_code", "http_status"):
            val = getattr(cur, attr, None)
            if isinstance(val, int) and val >= 100:
                return val
        resp = getattr(cur, "response", None)
        if resp is not None:
            sc = getattr(resp, "status_code", None)
            if isinstance(sc, int) and sc >= 100:
                return sc
        cur = cur.__cause__ or cur.__context__
    blob = _exc_blob(exc)
    m = re.search(r"\b(401|403|404|429)\b", blob)
    if m:
        return int(m.group(1))
    return None


def _map_gemini_exc(exc: BaseException) -> LlmError:
    if isinstance(exc, TimeoutError):
        return LlmError(503, "llm_timeout", "Gemini timed out")
    status = _http_status(exc)
    blob = _exc_blob(exc)
    if status in {401, 403}:
        return LlmError(502, "llm_upstream", "Gemini rejected the request")
    if (
        status == 429
        or "resourceexhausted" in blob.replace("_", "")
        or "resource exhausted" in blob
        or "quota" in blob
        or "rate limit" in blob
        or "ratelimit" in blob.replace(" ", "")
        or re.search(r"\b429\b", blob)
    ):
        return LlmError(503, "llm_quota", "Gemini quota or rate limit")
    if status == 404 or "not found" in blob or "not_found" in blob:
        return LlmError(502, "llm_upstream", "Gemini model not found (check GEMINI_MODEL)")
    return LlmError(502, "llm_upstream", f"Gemini request failed ({type(exc).__name__})")


def _should_try_next_model(mapped: LlmError) -> bool:
    if mapped.code == "llm_quota":
        return True
    return mapped.status == 502 and "not found" in mapped.detail.lower()


async def _call_with_fallback(invoke):
    """invoke(llm) -> awaitable. Retry 429 (1.5s, max 2); next model on 404/429."""
    last: LlmError | None = None
    models = _model_chain()
    for i, model in enumerate(models):
        retries = 0
        while True:
            try:
                llm = _build_gemini(model)
            except LlmError:
                raise
            except Exception as exc:
                raise LlmError(
                    502, "llm_upstream", f"Gemini client init failed ({type(exc).__name__})"
                ) from exc
            try:
                return await invoke(llm)
            except TimeoutError as exc:
                raise _map_gemini_exc(exc) from exc
            except LlmError:
                raise
            except Exception as exc:
                mapped = _map_gemini_exc(exc)
                last = mapped
                if mapped.code == "llm_quota" and retries < 2:
                    retries += 1
                    await asyncio.sleep(1.5)
                    continue
                if _should_try_next_model(mapped) and i < len(models) - 1:
                    break
                raise mapped from exc
    assert last is not None
    raise last


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

    async def _invoke(llm: Any) -> Any:
        return await asyncio.wait_for(
            llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)]),
            timeout=GEMINI_TIMEOUT_S,
        )

    msg = await _call_with_fallback(_invoke)
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
        async def _invoke(llm: Any) -> Any:
            structured = llm.with_structured_output(GeminiDecisionOut, method="json_schema")
            return await asyncio.wait_for(
                structured.ainvoke([SystemMessage(content=system), HumanMessage(content=user)]),
                timeout=GEMINI_TIMEOUT_S,
            )

        raw = await _call_with_fallback(_invoke)
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
