"""Agent 6 — Reporter: builds PR/Slack payload (Person 1 executes side-effects)."""

from __future__ import annotations

from .state_utils import append_event
from .types import (
    OverallSeverity,
    RedlineDiff,
    ReporterPayload,
    RiskFinding,
    RiskReport,
    SSEEvent,
    SpectreState,
    WorkflowPhase,
)


def _executive_summary(contract_id: str, report: RiskReport, redlines: int) -> str:
    violations = sum(1 for f in report.findings if f.status == "violation")
    at_risk = sum(1 for f in report.findings if f.status == "at_risk")
    return (
        f"Spectre reviewed `{contract_id}`: {violations} violations, {at_risk} at-risk clauses. "
        f"{redlines} redlines proposed. Overall: {report.overall.value.upper()}."
    )


def _pr_body(report: RiskReport, diff: RedlineDiff) -> str:
    lines = [
        "## Spectre risk report",
        "",
        f"**Overall severity:** `{report.overall.value}`",
        "",
        "### Findings",
        "",
        "| Clause | Status | Severity | Confidence | Summary |",
        "|--------|--------|----------|------------|---------|",
    ]
    for f in report.findings:
        lines.append(
            f"| {f.clause_id} | {f.status} | {f.severity.value} | {f.confidence:.2f} | {f.summary[:80]} |"
        )
    lines.append("")
    lines.append(diff.markdown_body)
    return "\n".join(lines)


def build_reporter_payload(state: SpectreState) -> ReporterPayload:
    report = RiskReport.model_validate(state["risk_report"])
    diff = RedlineDiff.model_validate(state.get("redline_diff") or {"contract_id": state["contract_id"], "items": [], "markdown_body": ""})
    contract_id = state["contract_id"]
    branch = f"spectre/legal-review-{contract_id}"

    return ReporterPayload(
        contract_id=contract_id,
        branch_name=branch,
        pr_title=f"[Spectre] Legal review — {contract_id} ({report.overall.value})",
        pr_body_markdown=_pr_body(report, diff),
        severity_label=report.overall,
        slack_summary=_executive_summary(contract_id, report, len(diff.items)),
        findings_count=len(report.findings),
        redline_count=len(diff.items),
    )


async def run_reporter_agent(state: SpectreState) -> SpectreState:
    """
    Person 1: after this node, fan-out to PyGithub + Slack + SSE complete.
    This node only materialises reporter_payload on state.
    """
    payload = build_reporter_payload(state)

    event = SSEEvent(
        contract_id=state["contract_id"],
        phase=WorkflowPhase.COMPLETE,
        message="Workflow complete — ready for PR and Slack",
        progress=100,
        payload={
            "severity": payload.severity_label.value,
            "findings_count": payload.findings_count,
            "redline_count": payload.redline_count,
            "branch_name": payload.branch_name,
        },
    )

    return {
        **state,
        "reporter_payload": payload.model_dump(),
        "phase": WorkflowPhase.COMPLETE.value,
        "sse_events": append_event(state, event),
    }
