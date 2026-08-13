from __future__ import annotations

import json
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


def previous_recommendations(limit: int = 5) -> list[dict[str, Any]]:
    if not _ready:
        init()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT payload FROM recommendations ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]
    finally:
        conn.close()


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
