"""
Risk Classifier Agent:
  - Takes clause manifest + regulation context
  - Calls Gemini with structured XML prompt
  - Parses XML response deterministically
  - Returns list of finding dicts
  - Includes reflection logic: if confidence < 0.72 → retry with enriched context
"""
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from app.agents.gemini_client import call_gemini

MAX_RETRIES = 2
CONFIDENCE_THRESHOLD = 0.72


def _build_prompt(clauses: List[Dict], regulation_summary: str, enrichment: str = "") -> str:
    clause_block = "\n".join(
        [f'<clause index="{c["index"]}">{c["text"][:800]}</clause>' for c in clauses[:30]]
    )
    return f"""You are a senior legal compliance AI. Analyse each contract clause against DPDP, GDPR, and RBI regulations.

REGULATION CONTEXT:
{regulation_summary}

{enrichment}

CONTRACT CLAUSES:
{clause_block}

For EACH clause, respond ONLY with XML in this exact format. No prose. No markdown. Only XML:

<findings>
  <finding>
    <clause_index>0</clause_index>
    <clause_text>exact text of the clause here</clause_text>
    <severity>low|medium|high|violation</severity>
    <confidence>0.0 to 1.0</confidence>
    <regulation_ref>e.g. DPDP Section 4(1)</regulation_ref>
    <regulation_body>DPDP|GDPR|RBI|NONE</regulation_body>
    <issue>One sentence describing the compliance issue, or "No issue found"</issue>
  </finding>
</findings>

Classify ALL clauses. Use severity=low for compliant clauses.
"""


def _parse_xml_findings(xml_text: str, contract_id: str, run_id: str) -> List[Dict]:
    """Parse Gemini XML response into a list of finding dicts."""
    findings = []
    # Strip any accidental markdown fences
    xml_text = xml_text.strip()
    if xml_text.startswith("```"):
        xml_text = "\n".join(xml_text.split("\n")[1:])
    if xml_text.endswith("```"):
        xml_text = "\n".join(xml_text.split("\n")[:-1])

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"[CLASSIFIER] XML parse error: {e}")
        return []

    for finding_el in root.findall("finding"):
        def get(tag):
            el = finding_el.find(tag)
            return el.text.strip() if el is not None and el.text else ""

        confidence_str = get("confidence")
        try:
            confidence = float(confidence_str)
        except ValueError:
            confidence = 0.5

        findings.append({
            "contract_id": contract_id,
            "run_id": run_id,
            "clause_index": int(get("clause_index") or 0),
            "clause_text": get("clause_text"),
            "severity": get("severity") or "low",
            "confidence": confidence,
            "regulation_ref": get("regulation_ref"),
            "regulation_body": get("regulation_body"),
            "issue": get("issue"),
            "needs_retry": confidence < CONFIDENCE_THRESHOLD,
        })
    return findings


async def classify_clauses(
    clauses: List[Dict],
    regulation_context: Dict,
    contract_id: str,
    run_id: str,
) -> List[Dict]:
    """
    Main classifier entry point.
    Runs classification, then reflection loop for low-confidence findings.
    """
    summary = regulation_context.get("summary", "")
    prompt = _build_prompt(clauses, summary)

    print(f"[CLASSIFIER] Sending {len(clauses)} clauses to Gemini...")
    raw = await call_gemini(prompt, use_pro=True)
    findings = _parse_xml_findings(raw, contract_id, run_id)
    print(f"[CLASSIFIER] Got {len(findings)} initial findings.")

    # Reflection loop — retry low-confidence findings
    low_conf = [f for f in findings if f.get("needs_retry")]
    if low_conf:
        print(f"[CLASSIFIER] Reflection loop: {len(low_conf)} low-confidence findings, retrying...")
        for finding in low_conf:
            if finding.get("retry_count", 0) >= MAX_RETRIES:
                continue
            enrichment = (
                f"EXTRA CONTEXT: Re-examine clause '{finding['clause_text'][:200]}'. "
                f"Focus specifically on {finding.get('regulation_body', 'all')} requirements."
            )
            retry_prompt = _build_prompt([{"index": finding["clause_index"], "text": finding["clause_text"]}], summary, enrichment)
            retry_raw = await call_gemini(retry_prompt, use_pro=True)
            retry_findings = _parse_xml_findings(retry_raw, contract_id, run_id)
            if retry_findings:
                # Replace original with higher-confidence result
                for i, f in enumerate(findings):
                    if f["clause_index"] == finding["clause_index"]:
                        findings[i] = {**retry_findings[0], "retry_count": finding.get("retry_count", 0) + 1}
                        break

    return findings
