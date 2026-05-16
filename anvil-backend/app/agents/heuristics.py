"""
Enterprise rule engine — $0 cost, no API.
Uses full DPDP/GDPR/RBI corpus + pattern library for risk + redline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .types import RegulationSnapshot, RiskFinding, Severity

# (regex, status, severity, summary template, cite frameworks)
PATTERNS: list[tuple[re.Pattern[str], str, Severity, str, list[str]]] = [
    (
        re.compile(r"unlimited\s+(?:sub[- ]?process|subcontract)", re.I),
        "violation",
        Severity.VIOLATION,
        "Unlimited sub-processor rights without notice or approval.",
        ["DPDP §8(3)", "GDPR Art.28"],
    ),
    (
        re.compile(r"sub[- ]?process.*(?:without\s+notice|sole\s+discretion)", re.I),
        "violation",
        Severity.VIOLATION,
        "Sub-processor engagement lacks prior notice or customer objection rights.",
        ["DPDP §8(3)", "GDPR Art.28"],
    ),
    (
        re.compile(r"(?:personal\s+data|customer\s+data).*(?:without\s+consent|no\s+consent)", re.I),
        "violation",
        Severity.VIOLATION,
        "Processing personal data without valid consent mechanism.",
        ["DPDP §6", "GDPR Art.6"],
    ),
    (
        re.compile(r"process(?:ing)?\s+personal\s+data", re.I),
        "at_risk",
        Severity.HIGH,
        "Data processing clause — verify consent, purpose limitation, and DPA flow-down.",
        ["DPDP §6", "GDPR Art.28"],
    ),
    (
        re.compile(r"retain.*(?:indefinite|perpetual|forever)", re.I),
        "at_risk",
        Severity.HIGH,
        "Indefinite data retention may violate storage limitation principles.",
        ["DPDP §8(4)", "GDPR Art.5(1)(e)"],
    ),
    (
        re.compile(r"(?:transfer|store|host).*(?:outside\s+india|united\s+states|third\s+countr)", re.I),
        "at_risk",
        Severity.HIGH,
        "Cross-border transfer requires safeguards and notified jurisdictions.",
        ["DPDP §11", "GDPR Art.44"],
    ),
    (
        re.compile(r"payment\s+(?:data|information)|transaction\s+data", re.I),
        "at_risk",
        Severity.HIGH,
        "Payment data may trigger RBI localisation requirements.",
        ["RBI DPSS-Circular-2018"],
    ),
    (
        re.compile(r"liabilit(?:y|ies).*(?:unlimited|uncapped)|unlimited\s+liabilit", re.I),
        "at_risk",
        Severity.MEDIUM,
        "Uncapped liability / broad indemnity requires legal review.",
        ["DPDP §18–22"],
    ),
    (
        re.compile(r"indemnif.*(?:penalt|regulat|fine)", re.I),
        "at_risk",
        Severity.MEDIUM,
        "Indemnity for regulatory penalties may be unenforceable.",
        ["DPDP §33"],
    ),
    (
        re.compile(r"(?:automated|solely\s+automated)\s+decision", re.I),
        "at_risk",
        Severity.HIGH,
        "Automated decision-making requires safeguards under GDPR Art.22.",
        ["GDPR Art.22"],
    ),
    (
        re.compile(r"(?:sell|share|disclose).*(?:third\s+part|affiliate).*marketing", re.I),
        "at_risk",
        Severity.MEDIUM,
        "Marketing data sharing requires explicit consent under DPDP.",
        ["DPDP Guidance-Marketing"],
    ),
    (
        re.compile(r"no\s+(?:audit|inspection)\s+right", re.I),
        "at_risk",
        Severity.MEDIUM,
        "Denial of audit rights conflicts with processor accountability.",
        ["DPDP Guidance-Audit", "GDPR Art.28(3)(h)"],
    ),
]


REDLINE_TEMPLATES: dict[str, str] = {
    "unlimited_subprocessor": (
        "The Vendor shall not engage any sub-processor without (i) thirty (30) days' prior written notice, "
        "(ii) Customer's right to object on reasonable grounds, and (iii) a written agreement imposing "
        "data protection obligations equivalent to this Agreement. Approved sub-processors are listed in Annex B."
    ),
    "consent": (
        "The Vendor shall process Personal Data only on Customer's documented instructions and, where required "
        "under the Digital Personal Data Protection Act 2023, only with valid, specific, informed, and "
        "unambiguous consent of the data principal."
    ),
    "retention": (
        "Upon termination or withdrawal of consent, the Vendor shall delete or return all Personal Data within "
        "thirty (30) days, except where retention is required by applicable law, and shall certify deletion in writing."
    ),
    "cross_border": (
        "Cross-border transfers shall occur only to jurisdictions notified under the DPDP Act or subject to "
        "approved contractual safeguards (including SCCs where applicable)."
    ),
    "audit": (
        "Customer may audit Vendor's compliance with this Section no less than once annually upon reasonable notice, "
        "or upon material security incident, including review of SOC 2 Type II or equivalent reports."
    ),
    "liability_cap": (
        "Each party's aggregate liability under this Agreement shall be capped at the fees paid in the twelve (12) "
        "months preceding the claim, except for breaches of confidentiality or data protection obligations."
    ),
}


@dataclass
class HeuristicResult:
    finding: RiskFinding
    redline_key: str | None = None


def _corpus_match(text: str, regs: RegulationSnapshot) -> HeuristicResult | None:
    lower = text.lower()
    weight_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    best_ref = None
    best_rank = 0
    for ref in regs.refs:
        for pattern in ref.contract_watch:
            if pattern.lower() in lower:
                rank = weight_rank.get(ref.risk_weight, 0)
                if rank >= best_rank:
                    best_rank = rank
                    best_ref = ref
    if not best_ref:
        return None
    status = "violation" if best_ref.risk_weight == "critical" else "at_risk"
    sev = (
        Severity.VIOLATION
        if best_ref.risk_weight == "critical"
        else Severity.HIGH
        if best_ref.risk_weight == "high"
        else Severity.MEDIUM
    )
    conf = 0.92 if best_ref.risk_weight == "critical" else 0.85
    redline_key = None
    if "sub" in lower and "process" in lower:
        redline_key = "unlimited_subprocessor"
    elif "consent" not in lower and "data" in lower:
        redline_key = "consent"
    elif "retain" in lower or "indefinite" in lower:
        redline_key = "retention"
    elif "transfer" in lower or "outside" in lower:
        redline_key = "cross_border"
    elif "audit" in lower:
        redline_key = "audit"
    return HeuristicResult(
        finding=RiskFinding(
            clause_id="",
            severity=sev,
            confidence=conf,
            status=status,  # type: ignore[arg-type]
            summary=f"Corpus match: {best_ref.title} ({best_ref.framework} {best_ref.section})",
            regulation_cites=[f"{best_ref.framework} {best_ref.section}"],
            needs_reflection=conf < 0.72,
        ),
        redline_key=redline_key,
    )


def analyze_clause(
    clause_id: str,
    text: str,
    category: str,
    regs: RegulationSnapshot,
    *,
    confidence_threshold: float = 0.72,
) -> HeuristicResult:
    corpus = _corpus_match(text, regs)
    if corpus:
        corpus.finding.clause_id = clause_id
        return corpus

    lower = text.lower()
    for pattern, status, severity, summary, cites in PATTERNS:
        if pattern.search(text):
            conf = 0.88 if severity == Severity.VIOLATION else 0.8
            if category == "data_processing" and "consent" not in lower and severity == Severity.HIGH:
                conf = 0.74  # trigger reflection
            redline_key = None
            if severity == Severity.VIOLATION and "sub" in lower:
                redline_key = "unlimited_subprocessor"
            elif "retain" in lower:
                redline_key = "retention"
            elif "transfer" in lower or "outside" in lower:
                redline_key = "cross_border"
            elif "liabilit" in lower:
                redline_key = "liability_cap"
            return HeuristicResult(
                finding=RiskFinding(
                    clause_id=clause_id,
                    severity=severity,
                    confidence=conf,
                    status=status,  # type: ignore[arg-type]
                    summary=summary,
                    regulation_cites=cites,
                    needs_reflection=conf < confidence_threshold,
                ),
                redline_key=redline_key,
            )

    if category == "data_processing" and "consent" not in lower:
        return HeuristicResult(
            finding=RiskFinding(
                clause_id=clause_id,
                severity=Severity.MEDIUM,
                confidence=0.75,
                status="at_risk",
                summary="Data processing clause should explicitly reference consent and purpose limitation.",
                regulation_cites=["DPDP §6"],
                needs_reflection=True,
            ),
            redline_key="consent",
        )

    return HeuristicResult(
        finding=RiskFinding(
            clause_id=clause_id,
            severity=Severity.COMPLIANT,
            confidence=0.86,
            status="compliant",
            summary="No high-priority regulatory pattern detected.",
            regulation_cites=[],
            needs_reflection=False,
        ),
    )


def apply_redline_template(clause_text: str, template_key: str | None, finding: RiskFinding) -> str:
    if template_key and template_key in REDLINE_TEMPLATES:
        return REDLINE_TEMPLATES[template_key]
    lower = clause_text.lower()
    if "unlimited" in lower and "sub" in lower:
        return REDLINE_TEMPLATES["unlimited_subprocessor"]
    if finding.status in ("violation", "at_risk") and "consent" in finding.summary.lower():
        return REDLINE_TEMPLATES["consent"]
    return (
        clause_text.rstrip()
        + "\n\n[Amended per Spectre recommendation: "
        + "; ".join(finding.regulation_cites or ["DPDP §8"])
        + "]"
    )
