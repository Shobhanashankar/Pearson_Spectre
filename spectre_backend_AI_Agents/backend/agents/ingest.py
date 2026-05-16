"""Agent 1 — Ingest: validate PDF or text, assign contract_id, emit SSE."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from config import MAX_UPLOAD_BYTES

from .errors import SpectreAgentError
from .state_utils import append_event
from .types import SSEEvent, SpectreState, WorkflowPhase


def _contract_id_from_bytes(data: bytes, filename: str) -> str:
    digest = hashlib.sha256(data).hexdigest()[:12]
    safe = "".join(c if c.isalnum() else "_" for c in Path(filename).stem)[:24]
    return f"{safe}_{digest}"


def validate_pdf(pdf_path: str) -> tuple[bytes, str]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if path.suffix.lower() not in (".pdf", ""):
        raise ValueError("Only PDF contracts are supported for file ingest")
    data = path.read_bytes()
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"PDF exceeds max size ({MAX_UPLOAD_BYTES // (1024*1024)} MB)")
    if len(data) < 100:
        raise ValueError("PDF file is too small or corrupt")
    if not data.startswith(b"%PDF"):
        raise ValueError("Invalid PDF header — file may be encrypted or not a PDF")
    if b"/Encrypt" in data[:65536]:
        raise ValueError("Password-protected PDFs are not supported — remove encryption and re-upload")
    return data, path.name


def validate_text(contract_text: str) -> str:
    text = (contract_text or "").strip()
    if len(text) < 40:
        raise ValueError("Contract text must be at least 40 characters")
    if len(text.encode("utf-8")) > MAX_UPLOAD_BYTES:
        raise ValueError("Contract text exceeds maximum allowed size")
    return text


async def run_ingest_agent(state: SpectreState) -> SpectreState:
    """
    Accepts pdf_path (input_type=pdf) OR contract_text (input_type=text).
    """
    input_type = state.get("input_type") or ("text" if state.get("contract_text") else "pdf")
    source = state.get("source_filename") or "contract"

    if input_type == "text":
        text = validate_text(state.get("contract_text", ""))
        data = text.encode("utf-8")
        contract_id = state.get("contract_id") or _contract_id_from_bytes(data, source)
        payload = {"source_filename": source, "input_type": "text", "chars": len(text)}
    else:
        pdf_path = state.get("pdf_path")
        if not pdf_path:
            raise SpectreAgentError(WorkflowPhase.INGEST, "pdf_path is required for PDF ingest")
        data, filename = validate_pdf(pdf_path)
        source = state.get("source_filename") or filename
        contract_id = state.get("contract_id") or _contract_id_from_bytes(data, source)
        payload = {"source_filename": source, "input_type": "pdf", "bytes": len(data)}

    event = SSEEvent(
        contract_id=contract_id,
        phase=WorkflowPhase.INGEST,
        message=f"Ingested {input_type} contract: {source}",
        progress=10,
        payload=payload,
    )

    return {
        **state,
        "contract_id": contract_id,
        "source_filename": source,
        "input_type": input_type,
        "phase": WorkflowPhase.INGEST.value,
        "sse_events": append_event(state, event),
        "errors": state.get("errors") or [],
        "reflection_passes": state.get("reflection_passes") or 0,
    }


def ingest_metadata_row(contract_id: str, pdf_path: str, source_filename: str) -> dict:
    """Person 1: INSERT into SQLite contracts table."""
    return {
        "contract_id": contract_id,
        "pdf_path": pdf_path,
        "source_filename": source_filename,
        "status": "ingested",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
