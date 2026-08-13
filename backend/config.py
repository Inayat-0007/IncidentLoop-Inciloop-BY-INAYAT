from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT / "data"))
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", DATA_DIR / "chroma"))
KNOWLEDGE_DIR = ROOT / "knowledge"
MEMORY_PATH = DATA_DIR / "memory.sqlite"

ROLLBACK_TOKEN = os.getenv("ROLLBACK_TOKEN", "replace_me_with_a_local_token")
WEB_ORIGIN = os.getenv("WEB_ORIGIN", "http://localhost:5173")

# TEST/CI ONLY. Default is off: live /investigate requires real Gemini.
# pytest and GitHub Actions set DEVOPSPILOT_FORCE_HEURISTIC=1.
def heuristic_enabled() -> bool:
    return os.getenv("DEVOPSPILOT_FORCE_HEURISTIC", "0") in {"1", "true", "True"}


GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "20"))
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "5"))

KNOWN_SERVICES = frozenset(
    {"checkout-api", "payment-api", "inventory-api", "auth-api", "catalog-api"}
)

EVIDENCE_MIN_FOR_ROLLBACK = 3
CONFIDENCE_MIN_FOR_ROLLBACK = 0.7
