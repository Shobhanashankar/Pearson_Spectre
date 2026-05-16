"""Agent error types and safe node wrapper for LangGraph."""

from __future__ import annotations

from typing import Awaitable, Callable

from .types import SSEEvent, SpectreState, WorkflowPhase


class SpectreAgentError(Exception):
    def __init__(self, phase: WorkflowPhase, message: str, *, recoverable: bool = False):
        super().__init__(message)
        self.phase = phase
        self.recoverable = recoverable


def _append_error_event(state: SpectreState, phase: WorkflowPhase, message: str) -> list[dict]:
    events = list(state.get("sse_events") or [])
    events.append(
        SSEEvent(
            contract_id=state.get("contract_id", "unknown"),
            phase=WorkflowPhase.ERROR,
            message=message,
            progress=0,
            payload={"failed_phase": phase.value, "detail": message},
        ).model_dump()
    )
    return events


def safe_node(
    phase: WorkflowPhase,
    fn: Callable[[SpectreState], Awaitable[SpectreState]],
) -> Callable[[SpectreState], Awaitable[SpectreState]]:
    """Wrap agent nodes: never crash graph; record errors on state."""

    async def wrapper(state: SpectreState) -> SpectreState:
        try:
            return await fn(state)
        except SpectreAgentError as e:
            errors = list(state.get("errors") or [])
            errors.append(f"{e.phase.value}: {e}")
            return {
                **state,
                "phase": WorkflowPhase.ERROR.value,
                "errors": errors,
                "sse_events": _append_error_event(state, e.phase, str(e)),
            }
        except Exception as e:
            errors = list(state.get("errors") or [])
            errors.append(f"{phase.value}: {e}")
            return {
                **state,
                "phase": WorkflowPhase.ERROR.value,
                "errors": errors,
                "sse_events": _append_error_event(state, phase, str(e)),
            }

    return wrapper
