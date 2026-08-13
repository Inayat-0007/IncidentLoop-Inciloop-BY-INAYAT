from __future__ import annotations

import json
import re
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR, MEMORY_PATH

_lock = threading.Lock()
_ready = False


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MEMORY_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    global _ready
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  incident_id TEXT,
                  role TEXT,
                  content TEXT,
                  ts TEXT
                );
                CREATE TABLE IF NOT EXISTS incidents (
                  id TEXT PRIMARY KEY,
                  payload TEXT,
                  ts TEXT
                );
                CREATE TABLE IF NOT EXISTS recommendations (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  incident_id TEXT,
                  payload TEXT,
                  ts TEXT
                );
                CREATE TABLE IF NOT EXISTS resolved (
                  incident_id TEXT PRIMARY KEY,
                  ts TEXT
                );
                """
            )
            conn.commit()
        finally:
            conn.close()
        _ready = True


def reset() -> None:
    """Wipe SQLite memory (tests)."""
    init()
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                "DELETE FROM conversations; DELETE FROM incidents; "
                "DELETE FROM recommendations; DELETE FROM resolved;"
            )
            conn.commit()
        finally:
            conn.close()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def save_incident(incident_id: str, payload: dict[str, Any]) -> None:
    if not _ready:
        init()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO incidents(id, payload, ts) VALUES (?, ?, ?)",
                (incident_id, json.dumps(payload), _now()),
            )
            conn.commit()
        finally:
            conn.close()


def get_incident(incident_id: str) -> dict[str, Any] | None:
    if not _ready:
        init()
    conn = _connect()
    try:
        row = conn.execute("SELECT payload FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return json.loads(row["payload"]) if row else None
    finally:
        conn.close()


def add_conversation(incident_id: str, role: str, content: str) -> None:
    if not _ready:
        init()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO conversations(incident_id, role, content, ts) VALUES (?, ?, ?, ?)",
                (incident_id, role, content, _now()),
            )
            conn.commit()
        finally:
            conn.close()


def save_recommendation(incident_id: str, payload: dict[str, Any]) -> None:
    if not _ready:
        init()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO recommendations(incident_id, payload, ts) VALUES (?, ?, ?)",
                (incident_id, json.dumps(payload), _now()),
            )
            conn.commit()
        finally:
            conn.close()


def conversation_history(limit: int = 12, incident_id: str | None = None) -> list[dict[str, str]]:
    if not _ready:
        init()
    conn = _connect()
    try:
        if incident_id:
            rows = conn.execute(
                "SELECT incident_id, role, content, ts FROM conversations "
                "WHERE incident_id = ? ORDER BY id DESC LIMIT ?",
                (incident_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT incident_id, role, content, ts FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "incident_id": r["incident_id"],
                "role": r["role"],
                "content": r["content"],
                "ts": r["ts"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def previous_recommendations(
    limit: int = 5,
    service: str | None = None,
    query: str | None = None,
) -> list[dict[str, Any]]:
    if not _ready:
        init()
    fetch = max(limit * 8, 20)
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT payload FROM recommendations ORDER BY id DESC LIMIT ?",
            (fetch,),
        ).fetchall()
        items = [json.loads(r["payload"]) for r in rows]
    finally:
        conn.close()
    if service:
        matched = [i for i in items if i.get("service") == service]
        if matched:
            items = matched
    if query:
        qtoks = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in items:
            blob = " ".join(
                [
                    str(item.get("reason") or ""),
                    " ".join(item.get("evidence") or []),
                    str(item.get("service") or ""),
                ]
            ).lower()
            overlap = len(qtoks & set(re.findall(r"[a-z0-9]+", blob)))
            scored.append((overlap, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        items = [s[1] for s in scored]
    return items[:limit]


def similar_incidents(service: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Read SQLite incidents for 'have we seen this before?' recall."""
    if not _ready:
        init()
    qtoks = set(re.findall(r"[a-z0-9]+", (query or "").lower()))
    conn = _connect()
    try:
        rows = conn.execute("SELECT id, payload, ts FROM incidents ORDER BY ts DESC").fetchall()
        resolved = {r["incident_id"] for r in conn.execute("SELECT incident_id FROM resolved")}
    finally:
        conn.close()
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        payload = json.loads(row["payload"])
        svc = str(payload.get("service") or "")
        prompt = str(payload.get("prompt") or "")
        ptoks = set(re.findall(r"[a-z0-9]+", prompt.lower()))
        overlap = len(qtoks & ptoks)
        if service and svc == service:
            overlap += 3
        if (payload.get("id") or row["id"]) in resolved or payload.get("status") == "verified":
            overlap += 2
        qlow = (query or "").lower()
        if "see this before" in qlow or "seen this before" in qlow:
            if (payload.get("id") or row["id"]) in resolved:
                overlap += 4
        if overlap <= 0:
            continue
        decision = payload.get("decision") or {}
        scored.append(
            (
                overlap,
                {
                    "id": payload.get("id") or row["id"],
                    "prompt": prompt,
                    "service": svc,
                    "recommendation": decision.get("recommendation"),
                    "status": payload.get("status"),
                    "resolved": (payload.get("id") or row["id"]) in resolved,
                    "ts": row["ts"],
                },
            )
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def mark_resolved(incident_id: str) -> None:
    if not _ready:
        init()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO resolved(incident_id, ts) VALUES (?, ?)",
                (incident_id, _now()),
            )
            conn.commit()
        finally:
            conn.close()


def dump_json_backup() -> Path:
    """Also keep a JSON snapshot for interview debugging."""
    if not _ready:
        init()
    conn = _connect()
    try:
        data = {
            "incidents": [json.loads(r["payload"]) for r in conn.execute("SELECT payload FROM incidents")],
            "recommendations": [
                json.loads(r["payload"]) for r in conn.execute("SELECT payload FROM recommendations")
            ],
            "resolved": [r["incident_id"] for r in conn.execute("SELECT incident_id FROM resolved")],
        }
    finally:
        conn.close()
    path = DATA_DIR / "memory.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path
