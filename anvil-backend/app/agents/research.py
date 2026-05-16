"""Agent 3 — Regulation researcher: local JSON + optional live web search."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state_utils import append_event
from .types import RegulationRef, RegulationSnapshot, SSEEvent, SpectreState, WorkflowPhase

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_rules(filename: str) -> list[dict[str, Any]]:
    path = DATA_DIR / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _rules_to_refs(framework: str, rules: list[dict[str, Any]]) -> list[RegulationRef]:
    refs: list[RegulationRef] = []
    for r in rules:
        refs.append(
            RegulationRef(
                framework=framework,  # type: ignore[arg-type]
                section=r["section"],
                title=r["title"],
                text=r["text"],
                source_url=r.get("source_url"),
                version=r.get("version", "2024-11"),
                tags=r.get("tags", []),
                keywords=r.get("keywords", []),
                risk_weight=r.get("risk_weight", "medium"),
                contract_watch=r.get("contract_watch", []),
            )
        )
    return refs


def _rule_matches_query(rule: dict[str, Any], q: str) -> bool:
    haystacks = [
        rule.get("section", ""),
        rule.get("title", ""),
        rule.get("text", ""),
        " ".join(rule.get("keywords", [])),
        " ".join(rule.get("tags", [])),
        " ".join(rule.get("contract_watch", [])),
    ]
    return any(q in h.lower() for h in haystacks if h)


async def web_search_regulation(query: str, framework: str) -> list[RegulationRef]:
    """
    Person 1 can inject a real search tool here via monkeypatch in tests.
    MVP: filter local JSON by keyword in section/title/text.
    """
    fname = {
        "DPDP": "dpdp_rules.json",
        "GDPR": "gdpr_rules.json",
        "RBI": "rbi_rules.json",
    }.get(framework, "dpdp_rules.json")
    rules = _load_rules(fname)
    q = query.lower()
    matched = [r for r in rules if _rule_matches_query(r, q)]
    return _rules_to_refs(framework, matched[:5])


_CATEGORY_TAG_MAP = {
    "data_processing": ["data_processing", "consent", "purpose_limitation", "lawful_basis"],
    "sub_processor": ["sub_processor", "processor", "dpa"],
    "liability": ["liability", "penalties"],
    "termination": ["termination", "exit"],
    "ip_ownership": ["definitions"],
    "general": ["definitions", "governance"],
}


def _filter_rules_for_categories(
    framework: str, rules: list[dict[str, Any]], categories: set[str]
) -> list[RegulationRef]:
    if not categories:
        return _rules_to_refs(framework, rules)
    wanted_tags: set[str] = set()
    for cat in categories:
        wanted_tags.update(_CATEGORY_TAG_MAP.get(cat, ["definitions"]))
    matched = [
        r for r in rules if wanted_tags.intersection(set(r.get("tags", []))) or r.get("risk_weight") == "critical"
    ]
    if len(matched) < 15:
        matched = rules
    return _rules_to_refs(framework, matched)


async def fetch_regulation_snapshot(
    contract_id: str,
    *,
    extra_queries: list[str] | None = None,
    clause_categories: set[str] | None = None,
) -> RegulationSnapshot:
    cats = clause_categories or set()
    dpdp = _filter_rules_for_categories("DPDP", _load_rules("dpdp_rules.json"), cats)
    gdpr = _filter_rules_for_categories("GDPR", _load_rules("gdpr_rules.json"), cats)
    rbi = _filter_rules_for_categories("RBI", _load_rules("rbi_rules.json"), cats)

    refs = dpdp + gdpr + rbi

    if extra_queries:
        for q in extra_queries:
            refs.extend(await web_search_regulation(q, "DPDP"))

    # de-dupe by section
    seen: set[str] = set()
    unique: list[RegulationRef] = []
    for ref in refs:
        key = f"{ref.framework}:{ref.section}"
        if key not in seen:
            seen.add(key)
            unique.append(ref)

    return RegulationSnapshot(
        contract_id=contract_id,
        refs=unique,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        cache_hit=not bool(extra_queries),
    )


async def fetch_specific_section(framework: str, section: str) -> RegulationRef | None:
    """Reflection loop: fetch one DPDP/GDPR subsection."""
    fname = (
        "dpdp_rules.json"
        if framework == "DPDP"
        else "gdpr_rules.json"
        if framework == "GDPR"
        else "rbi_rules.json"
    )
    for r in _load_rules(fname):
        if r["section"] == section or section in r["section"]:
            return RegulationRef(
                framework=framework,  # type: ignore[arg-type]
                section=r["section"],
                title=r["title"],
                text=r["text"],
                source_url=r.get("source_url"),
                version=r.get("version", "2024-11"),
                tags=r.get("tags", []),
                keywords=r.get("keywords", []),
                risk_weight=r.get("risk_weight", "medium"),
                contract_watch=r.get("contract_watch", []),
            )
    results = await web_search_regulation(section, framework)
    return results[0] if results else None


async def run_research_agent(state: SpectreState) -> SpectreState:
    """LangGraph parallel branch B (with extraction)."""
    contract_id = state["contract_id"]
    categories: set[str] = set()
    if state.get("clause_manifest"):
        from .types import ClauseManifest

        manifest = ClauseManifest.model_validate(state["clause_manifest"])
        categories = {c.category for c in manifest.clauses}
    snapshot = await fetch_regulation_snapshot(contract_id, clause_categories=categories)

    event = SSEEvent(
        contract_id=contract_id,
        phase=WorkflowPhase.RESEARCH,
        message=f"Loaded {len(snapshot.refs)} regulation references",
        progress=35,
        payload={"regulation_count": len(snapshot.refs)},
    )

    return {
        **state,
        "regulation_snapshot": snapshot.model_dump(),
        "phase": WorkflowPhase.RESEARCH.value,
        "sse_events": append_event(state, event),
    }
