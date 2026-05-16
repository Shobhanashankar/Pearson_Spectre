"""Reflection loop — LangGraph conditional edge (confidence < 0.72, max 2 retries)."""

from __future__ import annotations

from .research import fetch_specific_section
from .risk import classify_clauses
from config import MAX_GLOBAL_REFLECTION_PASSES

from .state_utils import append_event
from .types import (
    CONFIDENCE_THRESHOLD,
    MAX_REFLECTION_RETRIES,
    ClauseManifest,
    RegulationSnapshot,
    RiskReport,
    SSEEvent,
    SpectreState,
    WorkflowPhase,
)


def should_reflect(state: SpectreState) -> str:
    if state.get("phase") == WorkflowPhase.ERROR.value:
        return "continue"
    passes = state.get("reflection_passes") or 0
    if passes >= MAX_GLOBAL_REFLECTION_PASSES:
        return "continue"
    queue = state.get("reflection_queue") or []
    attempts = state.get("reflection_attempts") or {}
    for clause_id in queue:
        if attempts.get(clause_id, 0) < MAX_REFLECTION_RETRIES:
            return "reflect"
    return "continue"


async def run_reflection_agent(state: SpectreState) -> SpectreState:
    """Re-fetch regulation subsection for low-confidence clauses, re-classify only those."""
    manifest = ClauseManifest.model_validate(state["clause_manifest"])
    snapshot = RegulationSnapshot.model_validate(state["regulation_snapshot"])
    report = RiskReport.model_validate(state["risk_report"])
    attempts: dict[str, int] = dict(state.get("reflection_attempts") or {})

    queue = list(state.get("reflection_queue") or [])
    if not queue:
        return {**state, "phase": WorkflowPhase.REFLECTION.value}

    clause_id = queue[0]
    attempts[clause_id] = attempts.get(clause_id, 0) + 1

    clause = next((c for c in manifest.clauses if c.clause_id == clause_id), None)
    section_hint = clause.section_ref if clause else None
    query = section_hint or (clause.category if clause else "data processing")

    enriched_refs: list[dict] = list(state.get("reflection_enriched_refs") or [])
    for framework in ("DPDP", "GDPR", "RBI"):
        ref = await fetch_specific_section(framework, query)
        if ref:
            enriched_refs.append(ref.model_dump())
            snapshot.refs.append(ref)

    partial, _hints = await classify_clauses(
        manifest,
        snapshot,
        clause_ids=[clause_id],
        enriched_refs=enriched_refs,
    )

    by_id = {f.clause_id: f for f in report.findings}
    for f in partial.findings:
        f.reflection_attempts = attempts[clause_id]
        if f.confidence >= CONFIDENCE_THRESHOLD:
            f.needs_reflection = False
        by_id[f.clause_id] = f

    updated_findings = list(by_id.values())
    new_queue = [
        cid
        for cid in (state.get("reflection_queue") or [])
        if cid != clause_id
        and by_id.get(cid)
        and by_id[cid].needs_reflection
        and attempts.get(cid, 0) < MAX_REFLECTION_RETRIES
    ]
    # re-add if still low confidence after partial re-run
    if partial.findings and partial.findings[0].needs_reflection and clause_id not in new_queue:
        if attempts[clause_id] < MAX_REFLECTION_RETRIES:
            new_queue.append(clause_id)

    report.findings = updated_findings
    report.low_confidence_clause_ids = [f.clause_id for f in updated_findings if f.needs_reflection]

    event = SSEEvent(
        contract_id=state["contract_id"],
        phase=WorkflowPhase.REFLECTION,
        message=f"Reflection pass for {clause_id} (attempt {attempts[clause_id]})",
        progress=70,
        payload={"clause_id": clause_id, "remaining": len(new_queue)},
    )

    return {
        **state,
        "risk_report": report.model_dump(),
        "reflection_queue": new_queue,
        "reflection_attempts": attempts,
        "reflection_enriched_refs": enriched_refs,
        "reflection_passes": (state.get("reflection_passes") or 0) + 1,
        "regulation_snapshot": snapshot.model_dump(),
        "phase": WorkflowPhase.REFLECTION.value,
        "sse_events": append_event(state, event),
    }
