"""Shared clause splitting and categorization — no agent imports."""

from __future__ import annotations

import re

CLAUSE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("data_processing", re.compile(r"data\s+process|personal\s+data|processor", re.I)),
    ("sub_processor", re.compile(r"sub[-\s]?process|subcontractor", re.I)),
    ("liability", re.compile(r"liabilit|indemnif|damages|cap\s+on", re.I)),
    ("ip_ownership", re.compile(r"intellectual\s+property|ownership|license\s+grant", re.I)),
    ("termination", re.compile(r"terminat|notice\s+period|exit", re.I)),
]


def guess_category(text: str) -> str:
    for category, pattern in CLAUSE_PATTERNS:
        if pattern.search(text):
            return category
    return "general"


def split_into_clauses(full_text: str) -> list[tuple[str, str, int | None]]:
    """Split on numbered clauses (e.g. 14.3, Section 5)."""
    blocks: list[tuple[str, str, int | None]] = []
    parts = re.split(
        r"(?=(?:Section|Clause|Article)\s+\d+(?:\.\d+)*|\n\s*\d+\.\d+\s)",
        full_text,
        flags=re.I,
    )
    idx = 0
    for part in parts:
        part = part.strip()
        if len(part) < 80:
            continue
        title_match = re.match(
            r"^((?:Section|Clause|Article)\s+[\d.]+[^\n]{0,80})",
            part,
            re.I,
        )
        title = title_match.group(1).strip() if title_match else f"Clause block {idx + 1}"
        blocks.append((title, part[:4000], None))
        idx += 1
    if not blocks and full_text.strip():
        blocks.append(("Full document", full_text[:8000], None))
    return blocks
