"""Agent 2 — Extraction: PDF → typed clause manifest via pdfplumber."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

from ..config import MIN_CLAUSE_CHARS

from .clause_utils import guess_category, split_into_clauses
from .errors import SpectreAgentError
from .state_utils import append_event
from .text_extract import manifest_from_text
from .types import ClauseItem, ClauseManifest, SSEEvent, SpectreState, WorkflowPhase


def extract_clauses_from_pdf(pdf_path: str, contract_id: str, source_filename: str) -> ClauseManifest:
    pages_text: list[tuple[int, str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise SpectreAgentError(WorkflowPhase.EXTRACTION, "PDF has zero pages")
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages_text.append((i, text))

    full_text = "\n\n".join(t for _, t in pages_text if t)
    if len(full_text.strip()) < MIN_CLAUSE_CHARS:
        raise SpectreAgentError(
            WorkflowPhase.EXTRACTION,
            "No extractable text — PDF may be scanned/image-only. Use text paste or OCR first.",
            recoverable=False,
        )

    raw_blocks = split_into_clauses(full_text)

    clauses: list[ClauseItem] = []
    for i, (title, text, _) in enumerate(raw_blocks):
        if len(text.strip()) < MIN_CLAUSE_CHARS and len(raw_blocks) > 1:
            continue
        section_ref = None
        ref = re.search(r"(?:Section|Clause|Article)\s+([\d.]+)", title, re.I)
        if ref:
            section_ref = ref.group(1)
        page_num = None
        for pnum, ptext in pages_text:
            if text[:80] in ptext or title[:40] in ptext:
                page_num = pnum
                break
        clauses.append(
            ClauseItem(
                clause_id=f"{contract_id}_c{i:03d}",
                category=guess_category(text),  # type: ignore[arg-type]
                title=title[:200],
                text=text,
                page=page_num,
                section_ref=section_ref,
            )
        )

    return ClauseManifest(
        contract_id=contract_id,
        source_filename=source_filename,
        clauses=clauses,
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )


async def run_extraction_agent(state: SpectreState) -> SpectreState:
    """LangGraph parallel branch A — PDF or pasted text."""
    contract_id = state["contract_id"]
    source = state.get("source_filename") or "contract"
    input_type = state.get("input_type") or "pdf"

    if input_type == "text":
        manifest = manifest_from_text(
            contract_id,
            source,
            state.get("contract_text", ""),
            min_chars=MIN_CLAUSE_CHARS,
        )
    else:
        pdf_path = state.get("pdf_path")
        if not pdf_path:
            raise SpectreAgentError(WorkflowPhase.EXTRACTION, "pdf_path missing for PDF extraction")
        manifest = extract_clauses_from_pdf(pdf_path, contract_id, source)

    if not manifest.clauses:
        raise SpectreAgentError(WorkflowPhase.EXTRACTION, "No clauses extracted from contract")

    event = SSEEvent(
        contract_id=contract_id,
        phase=WorkflowPhase.EXTRACTION,
        message=f"Extracted {len(manifest.clauses)} clauses ({input_type})",
        progress=35,
        payload={
            "clause_count": len(manifest.clauses),
            "categories": list({c.category for c in manifest.clauses}),
        },
    )

    return {
        **state,
        "clause_manifest": manifest.model_dump(),
        "phase": WorkflowPhase.EXTRACTION.value,
        "sse_events": append_event(state, event),
    }
