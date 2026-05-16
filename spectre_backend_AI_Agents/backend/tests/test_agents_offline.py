"""Offline tests — no paid API required."""

import pytest

from agents.heuristics import analyze_clause
from agents.research import fetch_regulation_snapshot


SAMPLE_CLAUSE = (
    "Section 14.3. The Vendor may engage unlimited sub-processors worldwide without notice."
)


@pytest.mark.asyncio
async def test_corpus_flags_unlimited_subprocessor():
    snap = await fetch_regulation_snapshot("t")
    r = analyze_clause("c1", SAMPLE_CLAUSE, "sub_processor", snap)
    assert r.finding.status == "violation"
    assert r.finding.confidence >= 0.85


@pytest.mark.asyncio
async def test_e2e_demo_pipeline():
    from services.workflow import run_workflow

    text = """
    Section 14.3 Sub-processors. Unlimited sub-processing without notice.
    Section 8. Data Processing without consent.
    Section 22. Data transferred outside India without safeguards.
    """
    final = await run_workflow({
        "contract_text": text,
        "source_filename": "t.txt",
        "input_type": "text",
        "trigger": "text_upload",
        "sse_events": [],
        "errors": [],
    })
    assert final.get("phase") == "complete"
    assert final.get("reporter_payload")
