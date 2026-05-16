"""
Redline Agent:
  - Only runs on findings with severity medium / high / violation
  - Calls Gemini to generate a compliant rewrite + regulation cite
  - Returns enriched findings with rewrite_suggestion and regulation_cite
"""
from typing import List, Dict
from app.agents.gemini_client import call_gemini


def _build_redline_prompt(finding: Dict) -> str:
    return f"""You are a legal drafting expert. A contract clause has been flagged as non-compliant.

ORIGINAL CLAUSE:
{finding["clause_text"]}

COMPLIANCE ISSUE:
{finding.get("issue", "Non-compliant with " + finding.get("regulation_body", "applicable regulations"))}

REGULATION REFERENCE:
{finding.get("regulation_ref", "Applicable regulation")}

Provide a response ONLY in this XML format. No prose. No markdown:

<redline>
  <original>{finding["clause_text"]}</original>
  <proposed>Write a compliant replacement clause here. Be specific and legally precise.</proposed>
  <regulation_cite>Full citation e.g. DPDP Act 2023, Section 4(1)(b)</regulation_cite>
  <rationale>One sentence explaining why the proposed version is compliant.</rationale>
</redline>
"""


import xml.etree.ElementTree as ET


def _parse_redline(xml_text: str) -> Dict:
    xml_text = xml_text.strip().lstrip("```xml").rstrip("```").strip()
    try:
        root = ET.fromstring(xml_text)
        def get(tag):
            el = root.find(tag)
            return el.text.strip() if el is not None and el.text else ""
        return {
            "original_text": get("original"),
            "rewrite_suggestion": get("proposed"),
            "regulation_cite": get("regulation_cite"),
            "rationale": get("rationale"),
        }
    except ET.ParseError as e:
        print(f"[REDLINE] XML parse error: {e}")
        return {"rewrite_suggestion": "Unable to generate suggestion.", "regulation_cite": "", "original_text": ""}


async def redline_findings(findings: List[Dict]) -> List[Dict]:
    """
    For each finding with severity medium/high/violation,
    generate a rewrite suggestion.
    """
    actionable = {"medium", "high", "violation"}
    enriched = []
    for finding in findings:
        if finding.get("severity") in actionable:
            print(f"[REDLINE] Processing clause {finding.get('clause_index')} ({finding.get('severity')})...")
            prompt = _build_redline_prompt(finding)
            raw = await call_gemini(prompt, use_pro=True)
            redline = _parse_redline(raw)
            enriched.append({**finding, **redline})
        else:
            enriched.append(finding)
    return enriched
