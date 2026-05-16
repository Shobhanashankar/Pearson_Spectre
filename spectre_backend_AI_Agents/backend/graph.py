"""Enterprise LangGraph — 6 agents, safe nodes, parallel extract+research."""

from __future__ import annotations

import asyncio

from langgraph.graph import END, START, StateGraph

from agents.errors import safe_node
from services.omium_trace import trace_node
from agents.extraction import run_extraction_agent
from agents.ingest import run_ingest_agent
from agents.redline import run_redline_agent
from agents.reflection import run_reflection_agent, should_reflect
from agents.reporter import run_reporter_agent
from agents.research import run_research_agent
from agents.risk import run_risk_classifier_agent
from agents.state_utils import merge_states
from agents.types import SpectreState, WorkflowPhase


async def parallel_extract_research(state: SpectreState) -> SpectreState:
    if state.get("phase") == WorkflowPhase.ERROR.value:
        return state
    s1, s2 = await asyncio.gather(
        run_extraction_agent(dict(state)),
        run_research_agent(dict(state)),
    )
    merged = merge_states(state, s1, s2)
    if s1.get("phase") == WorkflowPhase.ERROR.value:
        return s1
    if s2.get("phase") == WorkflowPhase.ERROR.value:
        return s2
    merged["clause_manifest"] = s1.get("clause_manifest")
    merged["regulation_snapshot"] = s2.get("regulation_snapshot")
    # Re-fetch targeted regulations when clauses are known
    if merged.get("clause_manifest"):
        from agents.types import ClauseManifest
        from agents.research import fetch_regulation_snapshot

        manifest = ClauseManifest.model_validate(merged["clause_manifest"])
        cats = {c.category for c in manifest.clauses}
        snapshot = await fetch_regulation_snapshot(
            merged["contract_id"], clause_categories=cats
        )
        merged["regulation_snapshot"] = snapshot.model_dump()
    return merged


def build_spectre_graph():
    g = StateGraph(SpectreState)

    def traced(phase: WorkflowPhase, fn):
        return trace_node(phase.value)(safe_node(phase, fn))

    g.add_node("ingest", traced(WorkflowPhase.INGEST, run_ingest_agent))
    g.add_node("extract_research", traced(WorkflowPhase.EXTRACTION, parallel_extract_research))
    g.add_node("risk", traced(WorkflowPhase.RISK, run_risk_classifier_agent))
    g.add_node("reflection", traced(WorkflowPhase.REFLECTION, run_reflection_agent))
    g.add_node("redline", traced(WorkflowPhase.REDLINE, run_redline_agent))
    g.add_node("report", traced(WorkflowPhase.REPORT, run_reporter_agent))

    g.add_edge(START, "ingest")

    def after_ingest(state: SpectreState) -> str:
        return "error_end" if state.get("phase") == WorkflowPhase.ERROR.value else "extract_research"

    g.add_conditional_edges("ingest", after_ingest, {"extract_research": "extract_research", "error_end": END})

    def after_extract(state: SpectreState) -> str:
        return "error_end" if state.get("phase") == WorkflowPhase.ERROR.value else "risk"

    g.add_conditional_edges(
        "extract_research",
        after_extract,
        {"risk": "risk", "error_end": END},
    )

    g.add_conditional_edges(
        "risk",
        should_reflect,
        {"reflect": "reflection", "continue": "redline"},
    )
    g.add_edge("reflection", "risk")
    g.add_edge("redline", "report")
    g.add_edge("report", END)

    return g.compile()
