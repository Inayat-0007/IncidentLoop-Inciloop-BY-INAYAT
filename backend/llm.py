from __future__ import annotations

import hashlib
import os
from typing import Any

from backend.config import FORCE_HEURISTIC


def llm_available() -> bool:
    if FORCE_HEURISTIC:
        return False
    return bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("AZURE_OPENAI_API_KEY")
    )


def complete(system: str, user: str) -> str | None:
    """Vendor-neutral completion. Returns None when keys are absent or the call fails."""
    if not llm_available():
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception:
        return None

    llm: Any = None
    try:
        if os.getenv("GEMINI_API_KEY"):
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                google_api_key=os.getenv("GEMINI_API_KEY"),
            )
        elif os.getenv("AZURE_OPENAI_API_KEY"):
            from langchain_openai import AzureChatOpenAI

            llm = AzureChatOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            )
        elif os.getenv("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    except Exception:
        return None

    if llm is None:
        return None
    try:
        msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = getattr(msg, "content", None)
        return str(content) if content else None
    except Exception:
        return None


def stable_ms(seed: str, base: int = 80) -> float:
    n = int(hashlib.sha256(seed.encode()).hexdigest()[:4], 16)
    return float(base + (n % 40))
