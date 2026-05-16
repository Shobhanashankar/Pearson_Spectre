"""
Server-Sent Events (SSE) manager.
Frontend connects to /api/events/stream and receives live updates.
Backend calls sse_manager.publish(event) from anywhere.
"""
import asyncio
import json
from typing import Dict, Set, AsyncGenerator
from datetime import datetime


class SSEManager:
    def __init__(self):
        # run_id -> set of queues (one per connected client watching that run)
        self._queues: Dict[str, Set[asyncio.Queue]] = {}
        # global queues (dashboard feed)
        self._global_queues: Set[asyncio.Queue] = set()

    def _get_or_create(self, run_id: str) -> Set[asyncio.Queue]:
        if run_id not in self._queues:
            self._queues[run_id] = set()
        return self._queues[run_id]

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._get_or_create(run_id).add(q)
        return q

    async def subscribe_global(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._global_queues.add(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue):
        if run_id in self._queues:
            self._queues[run_id].discard(q)

    def unsubscribe_global(self, q: asyncio.Queue):
        self._global_queues.discard(q)

    async def publish(self, event_type: str, data: dict, run_id: str = None):
        """Publish an event to all subscribers (run-specific + global)."""
        payload = json.dumps({
            "type": event_type,
            "data": data,
            "ts": datetime.utcnow().isoformat(),
        })
        # run-specific
        if run_id and run_id in self._queues:
            dead = set()
            for q in self._queues[run_id]:
                try:
                    await q.put(payload)
                except Exception:
                    dead.add(q)
            self._queues[run_id] -= dead
        # global
        dead = set()
        for q in self._global_queues:
            try:
                await q.put(payload)
            except Exception:
                dead.add(q)
        self._global_queues -= dead

    async def stream(self, q: asyncio.Queue) -> AsyncGenerator[str, None]:
        """Yield SSE-formatted strings from the queue."""
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    # heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass


sse_manager = SSEManager()
