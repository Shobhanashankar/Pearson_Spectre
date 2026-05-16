"""Shared state helpers for agents."""

from __future__ import annotations

from .types import SSEEvent, SpectreState, WorkflowPhase


def append_event(state: SpectreState, event: SSEEvent) -> list[dict]:
    events = list(state.get("sse_events") or [])
    events.append(event.model_dump())
    return events


def merge_states(base: SpectreState, *updates: SpectreState) -> SpectreState:
    merged = dict(base)
    all_events = list(base.get("sse_events") or [])
    for u in updates:
        merged.update({k: v for k, v in u.items() if k != "sse_events"})
        all_events.extend(u.get("sse_events") or [])
    merged["sse_events"] = all_events
    return merged


def has_fatal_errors(state: SpectreState) -> bool:
    return state.get("phase") == WorkflowPhase.ERROR.value or bool(
        state.get("errors") and state.get("phase") == WorkflowPhase.ERROR.value
    )
