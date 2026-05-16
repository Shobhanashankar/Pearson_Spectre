"""SQLite persistence for contracts, workflow runs, and SSE events."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from config import DB_PATH


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id TEXT PRIMARY KEY,
                source_filename TEXT NOT NULL,
                pdf_path TEXT,
                input_type TEXT NOT NULL DEFAULT 'pdf',
                status TEXT NOT NULL DEFAULT 'pending',
                overall_severity TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                status TEXT NOT NULL,
                state_json TEXT,
                errors_json TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
            );
            CREATE TABLE IF NOT EXISTS sse_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id TEXT NOT NULL,
                run_id TEXT,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
            );
            CREATE INDEX IF NOT EXISTS idx_sse_contract ON sse_events(contract_id);
            CREATE INDEX IF NOT EXISTS idx_runs_contract ON workflow_runs(contract_id);
            """
        )


def upsert_contract(
    contract_id: str,
    source_filename: str,
    *,
    pdf_path: str | None = None,
    input_type: str = "pdf",
    status: str = "pending",
    overall_severity: str | None = None,
) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO contracts (contract_id, source_filename, pdf_path, input_type, status, overall_severity, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(contract_id) DO UPDATE SET
                status=excluded.status,
                overall_severity=COALESCE(excluded.overall_severity, contracts.overall_severity),
                updated_at=excluded.updated_at
            """,
            (contract_id, source_filename, pdf_path, input_type, status, overall_severity, now, now),
        )


def save_run(run_id: str, contract_id: str, status: str, state: dict[str, Any], errors: list[str]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO workflow_runs (run_id, contract_id, status, state_json, errors_json, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, COALESCE((SELECT started_at FROM workflow_runs WHERE run_id=?), ?), ?)
            """,
            (
                run_id,
                contract_id,
                status,
                json.dumps(state, default=str),
                json.dumps(errors),
                run_id,
                _utc_now(),
                _utc_now() if status in ("complete", "error") else None,
            ),
        )


def append_sse_event(contract_id: str, run_id: str | None, event: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sse_events (contract_id, run_id, event_json, created_at) VALUES (?, ?, ?, ?)",
            (contract_id, run_id, json.dumps(event), _utc_now()),
        )


def get_sse_events(contract_id: str, after_id: int = 0) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, event_json FROM sse_events WHERE contract_id=? AND id>? ORDER BY id",
            (contract_id, after_id),
        ).fetchall()
    return [{"id": r["id"], **json.loads(r["event_json"])} for r in rows]


def get_contract(contract_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM contracts WHERE contract_id=?", (contract_id,)).fetchone()
    return dict(row) if row else None


def get_latest_run_state(contract_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT state_json FROM workflow_runs WHERE contract_id=? ORDER BY started_at DESC LIMIT 1",
            (contract_id,),
        ).fetchone()
    if not row or not row["state_json"]:
        return None
    return json.loads(row["state_json"])
