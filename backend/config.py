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


def data_source() -> str:
    """Live default is company files. `sim` is pytest/CI only (`DATA_SOURCE=sim`)."""
    raw = (os.getenv("DATA_SOURCE") or "files").strip().lower()
    if raw in {"files", "http", "github", "sim"}:
        return raw
    return "files"


def company_data_dir() -> Path:
    override = os.getenv("COMPANY_DATA_DIR")
    if override:
        return Path(override)
    return DATA_DIR / "company"


def metrics_url() -> str:
    return (os.getenv("METRICS_URL") or "").strip()


def logs_url() -> str:
    return (os.getenv("LOGS_URL") or "").strip()


def releases_url() -> str:
    return (os.getenv("RELEASES_URL") or "").strip()


def github_repo() -> str:
    return (os.getenv("GITHUB_REPO") or "").strip()


def github_token() -> str:
    return (os.getenv("GITHUB_TOKEN") or "").strip()


def rollback_webhook_url() -> str:
    return (os.getenv("ROLLBACK_WEBHOOK_URL") or "").strip()


GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "20"))
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "5"))

KNOWN_SERVICES = frozenset(
    {"checkout-api", "payment-api", "inventory-api", "auth-api", "catalog-api"}
)

EVIDENCE_MIN_FOR_ROLLBACK = 3
CONFIDENCE_MIN_FOR_ROLLBACK = 0.7
