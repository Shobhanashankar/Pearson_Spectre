"""Agent 4 — Risk classifier: Gemini + enterprise heuristics (free fallback)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from ..config import CONFIDENCE_THRESHOLD, LLM_BATCH_SIZE

from .heuristics import analyze_clause
from .llm import complete_xml, extract_xml_from_response, load_prompt, llm_available
from .state_utils import append_event
from .types import (
    ClauseManifest,
    OverallSeverity,
    RegulationSnapshot,
    RiskFinding,
    RiskReport,
    Severity,
    SSEEvent,
    SpectreState,
    WorkflowPhase,
)

# Cache redline hints on state between risk → redline
REDLINE_HINTS_KEY = "_redline_hints"


def _parse_risk_xml(xml_text: str) -> list[dict[str, Any]]:
    wrapped = extract_xml_from_response(xml_text, "risk_report")
    if "<finding" not in wrapped and "<risk_report" not in wrapped:
        raise ValueError("No risk_report XML in Gemini response")
    root = ET.fromstring(wrapped)
    findings: list[dict[str, Any]] = []
    for node in root.findall(".//finding"):
        findings.append(
            {
                "clause_id": node.findtext("clause_id", ""),
                "severity": node.findtext("severity", "low"),
                "confidence": float(node.findtext("confidence", "0.5")),
                "status": node.findtext("status", "at_risk"),
                "summary": node.findtext("summary", ""),
                "regulation_cites": [
                    c.text or "" for c in node.findall("./regulation_cites/cite")
                ],
            }
        )
    return findings


def _overall_severity(findings: list[RiskFinding]) -> OverallSeverity:
    if any(f.severity == Severity.VIOLATION or f.status == "violation" for f in findings):
        return OverallSeverity.RED
    if any(f.severity in (Severity.HIGH, Severity.MEDIUM) or f.status == "at_risk" for f in findings):
        return OverallSeverity.AMBER
    return OverallSeverity.GREEN


def _merge_finding(heuristic: RiskFinding, llm: RiskFinding | None) -> RiskFinding:
    """Prefer higher severity; boost confidence when both agree."""
    if llm is None:
        return heuristic
    rank = {Severity.COMPLIANT: 0, Severity.LOW: 1, Severity.MEDIUM: 2, Severity.HIGH: 3, Severity.VIOLATION: 4}
    pick = llm if rank.get(llm.severity, 0) >= rank.get(heuristic.severity, 0) else heuristic
    other = heuristic if pick is llm else llm
    if pick.status == other.status:
        pick.confidence = min(0.98, (pick.confidence + other.confidence) / 2 + 0.05)
    pick.regulation_cites = list(dict.fromkeys((pick.regulation_cites or []) + (other.regulation_cites or [])))
    pick.needs_reflection = pick.confidence < CONFIDENCE_THRESHOLD
    return pick


async def classify_clauses(
    manifest: ClauseManifest,
    snapshot: RegulationSnapshot,
    *,
    clause_ids: list[str] | None = None,
    enriched_refs: list[dict[str, Any]] | None = None,
) -> tuple[RiskReport, dict[str, str | None]]:
    targets = manifest.clauses
    if clause_ids:
        targets = [c for c in manifest.clauses if c.clause_id in clause_ids]

    redline_hints: dict[str, str | None] = {}
    llm_by_id: dict[str, RiskFinding] = {}

    if llm_available():
        prompt = load_prompt("risk_classifier")
        for i in range(0, len(targets), LLM_BATCH_SIZE):
            batch = targets[i : i + LLM_BATCH_SIZE]
            payload = {
                "clauses": [c.model_dump() for c in batch],
                "regulations": [r.model_dump() for r in snapshot.refs[:80]],
                "enriched_regulations": enriched_refs or [],
            }
            try:
                raw = await complete_xml(prompt, payload, xml_root="risk_report")
                for row in _parse_risk_xml(raw):
                    if not row.get("clause_id"):
                        continue
                    conf = float(row["confidence"])
                    llm_by_id[row["clause_id"]] = RiskFinding(
                        clause_id=row["clause_id"],
                        severity=Severity(row["severity"]),
                        confidence=conf,
                        status=row["status"],  # type: ignore[arg-type]
                        summary=row["summary"],
                        regulation_cites=row.get("regulation_cites") or [],
                        needs_reflection=conf < CONFIDENCE_THRESHOLD,
                    )
            except Exception:
                break

    findings: list[RiskFinding] = []
    for clause in targets:
        hr = analyze_clause(clause.clause_id, clause.text, clause.category, snapshot)
        redline_hints[clause.clause_id] = hr.redline_key
        merged = _merge_finding(hr.finding, llm_by_id.get(clause.clause_id))
        findings.append(merged)

    low = [f.clause_id for f in findings if f.needs_reflection]
    report = RiskReport(
        contract_id=manifest.contract_id,
        findings=findings,
        overall=_overall_severity(findings),
        low_confidence_clause_ids=low,
    )
    return report, redline_hints


async def run_risk_classifier_agent(state: SpectreState) -> SpectreState:
    manifest = ClauseManifest.model_validate(state["clause_manifest"])
    snapshot = RegulationSnapshot.model_validate(state["regulation_snapshot"])
    enriched = state.get("reflection_enriched_refs")

    report, hints = await classify_clauses(
        manifest,
        snapshot,
        enriched_refs=enriched if isinstance(enriched, list) else None,
    )

    violations = sum(1 for f in report.findings if f.status == "violation")
    event = SSEEvent(
        contract_id=state["contract_id"],
        phase=WorkflowPhase.RISK,
        message=f"Classified {len(report.findings)} clauses ({violations} violations)",
        progress=60,
        payload={
            "overall": report.overall.value,
            "violations": violations,
            "low_confidence": report.low_confidence_clause_ids,
            "llm_used": llm_available(),
        },
    )

    return {
        **state,
        "risk_report": report.model_dump(),
        "reflection_queue": report.low_confidence_clause_ids,
        REDLINE_HINTS_KEY: hints,
        "phase": WorkflowPhase.RISK.value,
        "sse_events": append_event(state, event),
    }
