"""
Research Agent:
  - Loads local regulation rules JSON files (DPDP, GDPR, RBI)
  - Uses Gemini to refine regulation context for classification guidance
  - Returns consolidated regulation context
"""
import json, os
from typing import Dict, Any
from app.agents.gemini_client import call_gemini

RULES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "regulations")


def load_local_rules(regulation: str = None) -> Dict[str, Any]:
    """Load all or a specific regulation from local JSON files."""
    rules = {}
    for fname in ["dpdp_rules.json", "gdpr_rules.json", "rbi_rules.json"]:
        fpath = os.path.join(RULES_DIR, fname)
        key = fname.replace("_rules.json", "").upper()
        if regulation and key != regulation.upper():
            continue
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                rules[key] = json.load(f)
        else:
            print(f"[RESEARCH] Warning: {fpath} not found. Using empty stub.")
            rules[key] = {"rules": [], "summary": f"{key} rules file missing."}
    return rules


async def research_regulations(clause_texts: list = None) -> Dict[str, Any]:
    """
    Main entry point for the research agent.
    1. Loads local rules
    2. If clause_texts provided, refines guidance using Gemini and local regulation summaries
    """
    local_rules = load_local_rules()

    # Build a brief summary for LangGraph state
    summary_lines = []
    for reg_name, reg_data in local_rules.items():
        summary = reg_data.get("summary", "")
        rule_count = len(reg_data.get("rules", []))
        summary_lines.append(f"{reg_name}: {rule_count} rules. {summary}")

    base_summary = "\n".join(summary_lines)
    regulation_context = {
        "rules": local_rules,
        "summary": base_summary,
    }

    if clause_texts:
        try:
            research_prompt = (
                "You are a regulatory research assistant. "
                "Given the following contract clauses and summaries of DPDP, GDPR, and RBI requirements, "
                "produce a concise regulation_context summary that will help a contract classifier assess compliance."\
                f"\n\nCONTRACT CLAUSES:\n{chr(10).join(clause_texts[:10])}\n\nREGULATION SUMMARY:\n{base_summary}"
            )
            refinement = await call_gemini(research_prompt, use_pro=False)
            regulation_context["summary"] = f"{base_summary}\n\nResearch note: {refinement}".strip()
        except Exception as e:
            print(f"[RESEARCH] Gemini refinement failed: {e}")

    print(f"[RESEARCH] Loaded regulations: {list(local_rules.keys())}")
    return regulation_context
