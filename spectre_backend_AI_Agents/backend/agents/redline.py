"""Agent 5 — Redline: templates + optional Gemini."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .heuristics import apply_redline_template
from .llm import complete_xml, extract_xml_from_response, load_prompt, llm_available
from .risk import REDLINE_HINTS_KEY
from .state_utils import append_event
from .types import (
    ClauseManifest,
    RedlineDiff,
    RedlineItem,
    RiskReport,
    Severity,
    SSEEvent,
    SpectreState,
    WorkflowPhase,
)


def _parse_redline_xml(xml_text: str) -> list[dict]:
    wrapped = extract_xml_from_response(xml_text, "redline_diff")
    if "<redline_diff" not in wrapped:
        raise ValueError("No redline_diff XML")
    root = ET.fromstring(wrapped)
    return [
        {
            "clause_id": node.findtext("clause_id", ""),
            "original_text": node.findtext("original_text", ""),
            "proposed_text": node.findtext("proposed_text", ""),
            "rationale": node.findtext("rationale", ""),
            "regulation_cites": [c.text or "" for c in node.findall("./regulation_cites/cite")],
        }
        for node in root.findall(".//item")
    ]


def _markdown_diff(items: list[RedlineItem]) -> str:
    lines = ["## Proposed redlines\n"]
    for item in items:
        lines.append(f"### Clause `{item.clause_id}`\n")
        lines.append("**Regulation:** " + ", ".join(item.regulation_cites) + "\n")
        lines.append(f"*{item.rationale}*\n")
        lines.append("```diff")
        lines.append("- " + item.original_text[:600].replace("\n", " "))
        lines.append("+ " + item.proposed_text[:600].replace("\n", " "))
        lines.append("```\n")
    return "\n".join(lines)


async def run_redline_agent(state: SpectreState) -> SpectreState:
    manifest = ClauseManifest.model_validate(state["clause_manifest"])
    report = RiskReport.model_validate(state["risk_report"])
    hints: dict[str, str | None] = state.get(REDLINE_HINTS_KEY) or {}

    actionable = {
        f.clause_id: f
        for f in report.findings
        if f.severity in (Severity.MEDIUM, Severity.HIGH, Severity.VIOLATION)
        or f.status in ("at_risk", "violation")
    }
    clauses_by_id = {c.clause_id: c for c in manifest.clauses}
    items: list[RedlineItem] = []
    llm_ids: set[str] = set()

    if actionable and llm_available():
        try:
            prompt = load_prompt("redline")
            payload = {
                "findings": [actionable[cid].model_dump() for cid in actionable],
                "clauses": [clauses_by_id[cid].model_dump() for cid in actionable if cid in clauses_by_id],
            }
            raw = await complete_xml(prompt, payload, xml_root="redline_diff")
            for row in _parse_redline_xml(raw):
                if row.get("clause_id"):
                    items.append(RedlineItem(**row))
                    llm_ids.add(row["clause_id"])
        except Exception:
            pass

    for cid, finding in actionable.items():
        if cid in llm_ids:
            continue
        clause = clauses_by_id.get(cid)
        if not clause:
            continue
        proposed = apply_redline_template(clause.text, hints.get(cid), finding)
        items.append(
            RedlineItem(
                clause_id=cid,
                original_text=clause.text[:2000],
                proposed_text=proposed,
                regulation_cites=finding.regulation_cites or ["DPDP §8"],
                rationale=finding.summary,
            )
        )

    diff = RedlineDiff(
        contract_id=state["contract_id"],
        items=items,
        markdown_body=_markdown_diff(items),
    )

    event = SSEEvent(
        contract_id=state["contract_id"],
        phase=WorkflowPhase.REDLINE,
        message=f"Generated {len(items)} redlines",
        progress=85,
        payload={"redline_count": len(items)},
    )

    return {
        **state,
        "redline_diff": diff.model_dump(),
        "phase": WorkflowPhase.REDLINE.value,
        "sse_events": append_event(state, event),
    }
