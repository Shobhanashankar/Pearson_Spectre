"""Omium-style span instrumentation for workflow observability."""
import json, time, uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
import aiosqlite
from app.db.database import DB_PATH


@asynccontextmanager
async def omium_span(trace_id: str, run_id: Optional[str], span_name: str, parent_span_id: str = None, attributes: dict = None):
    started_at = datetime.utcnow().isoformat()
    start_ts = time.time()
    span_id = str(uuid.uuid4())
    status = "ok"
    try:
        yield span_id
    except Exception:
        status = "error"
        raise
    finally:
        ended_at = datetime.utcnow().isoformat()
        latency_ms = int((time.time() - start_ts) * 1000)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO trace_spans
                   (id, trace_id, run_id, span_name, parent_span_id,
                    started_at, ended_at, latency_ms, status, attributes)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    span_id,
                    trace_id,
                    run_id,
                    span_name,
                    parent_span_id,
                    started_at,
                    ended_at,
                    latency_ms,
                    status,
                    json.dumps(attributes or {}),
                ),
            )
            await db.commit()
