"""Shared contracts for Person 1 (LangGraph), Person 2 (agents), Person 3 (SSE UI)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


# --- Enums (mirror frontend badge + PR label) ---


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VIOLATION = "violation"
    COMPLIANT = "compliant"


class WorkflowPhase(str, Enum):
    INGEST = "ingest"
    EXTRACTION = "extraction"
    RESEARCH = "research"
    RISK = "risk"
    REFLECTION = "reflection"
    REDLINE = "redline"
    REPORT = "report"
    COMPLETE = "complete"
    ERROR = "error"


class OverallSeverity(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


# --- Structured agent outputs ---


class ClauseItem(BaseModel):
    clause_id: str
    category: Literal[
        "data_processing",
        "liability",
        "ip_ownership",
        "termination",
        "sub_processor",
        "general",
    ]
    title: str
    text: str
    page: int | None = None
    section_ref: str | None = None


class ClauseManifest(BaseModel):
    contract_id: str
    source_filename: str
    clauses: list[ClauseItem]
    extracted_at: str


class RegulationRef(BaseModel):
    framework: Literal["DPDP", "GDPR", "RBI"]
    section: str
    title: str
    text: str
    source_url: str | None = None
    version: str = "2024-11"
    tags: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    risk_weight: Literal["critical", "high", "medium", "low"] = "medium"
    contract_watch: list[str] = Field(default_factory=list)


class RegulationSnapshot(BaseModel):
    contract_id: str
    refs: list[RegulationRef]
    fetched_at: str
    cache_hit: bool = False


class RiskFinding(BaseModel):
    clause_id: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["compliant", "at_risk", "violation"]
    summary: str
    regulation_cites: list[str] = Field(default_factory=list)
    needs_reflection: bool = False
    reflection_attempts: int = 0


class RiskReport(BaseModel):
    contract_id: str
    findings: list[RiskFinding]
    overall: OverallSeverity
    low_confidence_clause_ids: list[str] = Field(default_factory=list)


class RedlineItem(BaseModel):
    clause_id: str
    original_text: str
    proposed_text: str
    regulation_cites: list[str]
    rationale: str


class RedlineDiff(BaseModel):
    contract_id: str
    items: list[RedlineItem]
    markdown_body: str


class ReporterPayload(BaseModel):
    """Person 1 passes this to PyGithub + Slack; Person 3 reads via SSE."""

    contract_id: str
    branch_name: str
    pr_title: str
    pr_body_markdown: str
    severity_label: OverallSeverity
    slack_summary: str
    findings_count: int
    redline_count: int


# --- LangGraph state (Person 1 owns graph; Person 2 owns field semantics) ---


class SpectreState(TypedDict, total=False):
    contract_id: str
    run_id: str
    pdf_path: str
    contract_text: str
    input_type: Literal["pdf", "text"]
    source_filename: str
    focus_frameworks: list[str]
    trigger: Literal["contract_webhook", "regulation_webhook", "manual_upload", "text_upload"]
    reflection_passes: int
    phase: str
    clause_manifest: dict[str, Any]
    regulation_snapshot: dict[str, Any]
    risk_report: dict[str, Any]
    redline_diff: dict[str, Any]
    reporter_payload: dict[str, Any]
    reflection_queue: list[str]
    reflection_attempts: dict[str, int]
    reflection_enriched_refs: list[dict[str, Any]]
    _redline_hints: dict[str, str | None]
    errors: list[str]
    sse_events: list[dict[str, Any]]


# --- SSE event shape (Person 1 emits; Person 3 consumes) ---


class SSEEvent(BaseModel):
    contract_id: str
    phase: WorkflowPhase
    message: str
    progress: int = Field(ge=0, le=100)
    payload: dict[str, Any] | None = None


CONFIDENCE_THRESHOLD = 0.72
MAX_REFLECTION_RETRIES = 2
