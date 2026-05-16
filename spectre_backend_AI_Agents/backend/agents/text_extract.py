"""Text / paste ingest — builds clause manifest without PDF."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .clause_utils import guess_category, split_into_clauses
from .types import ClauseItem, ClauseManifest


def manifest_from_text(
    contract_id: str,
    source_filename: str,
    raw_text: str,
    *,
    min_chars: int = 40,
) -> ClauseManifest:
    text = raw_text.strip()
    if len(text) < min_chars:
        raise ValueError(f"Contract text too short (min {min_chars} characters)")

    blocks = split_into_clauses(text)
    if not blocks:
        blocks = [("Full document", text[:12000], None)]

    clauses: list[ClauseItem] = []
    for i, (title, block, page) in enumerate(blocks):
        if len(block.strip()) < min_chars and len(blocks) > 1:
            continue
        section_ref = None
        ref = re.search(r"(?:Section|Clause|Article)\s+([\d.]+)", title, re.I)
        if ref:
            section_ref = ref.group(1)
        clauses.append(
            ClauseItem(
                clause_id=f"{contract_id}_c{i:03d}",
                category=guess_category(block),  # type: ignore[arg-type]
                title=title[:200],
                text=block,
                page=page,
                section_ref=section_ref,
            )
        )

    if not clauses:
        clauses.append(
            ClauseItem(
                clause_id=f"{contract_id}_c000",
                category="general",
                title="Full document",
                text=text[:12000],
            )
        )

    return ClauseManifest(
        contract_id=contract_id,
        source_filename=source_filename,
        clauses=clauses,
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )
