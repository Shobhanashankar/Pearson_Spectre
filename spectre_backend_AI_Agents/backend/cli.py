"""Spectre CLI — test full pipeline without frontend."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env")
    except ImportError:
        pass


def _print_health() -> None:
    import importlib
    llm = importlib.import_module("agents.llm")
    get_provider = llm.get_provider
    llm_available = llm.llm_available
    from config import GEMINI_API_KEY, GEMINI_MODEL, OMIUM_API_KEY
    from services.omium_trace import omium_configured

    print("\n=== Spectre Health ===")
    print(f"  Gemini key set:     {bool(GEMINI_API_KEY)}")
    print(f"  Gemini model:       {GEMINI_MODEL}")
    print(f"  LLM provider:       {get_provider()}")
    print(f"  LLM active:         {llm_available()}")
    print(f"  Omium key set:      {bool(OMIUM_API_KEY)}")
    print(f"  Omium configured:   {omium_configured()}")
    print(f"  Heuristic engine:   always on (89 rules)")
    print()


def _print_results(final: dict, verbose: bool) -> None:
    print("\n=== Spectre Results ===")
    print(f"  Contract ID:  {final.get('contract_id')}")
    print(f"  Phase:        {final.get('phase')}")
    payload = final.get("reporter_payload") or {}
    print(f"  Severity:     {payload.get('severity_label', 'n/a')}")
    print(f"  Summary:      {payload.get('slack_summary', 'n/a')}")

    report = final.get("risk_report") or {}
    findings = report.get("findings") or []
    if findings:
        print(f"\n  Findings ({len(findings)}):")
        print(f"  {'Clause':<28} {'Status':<12} {'Severity':<10} {'Conf':<6} Summary")
        print("  " + "-" * 90)
        for f in findings:
            print(
                f"  {f.get('clause_id','')[:28]:<28} "
                f"{f.get('status',''):<12} "
                f"{f.get('severity',''):<10} "
                f"{f.get('confidence',0):.2f}   "
                f"{(f.get('summary') or '')[:45]}"
            )

    diff = final.get("redline_diff") or {}
    items = diff.get("items") or []
    if items and verbose:
        print(f"\n  Redlines ({len(items)}):")
        for it in items:
            print(f"    - {it.get('clause_id')}: {it.get('rationale', '')[:60]}")

    if final.get("errors"):
        print(f"\n  Errors: {final['errors']}")
    if final.get("side_effects"):
        print(f"\n  Side effects: {json.dumps(final['side_effects'], indent=2)}")
    out = Path(__file__).parent / "output"
    if out.exists():
        print(f"\n  Artifacts: {out.resolve()}")
    print()


async def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(description="Spectre — contract compliance CLI")
    parser.add_argument("--pdf", type=str, help="Path to contract PDF")
    parser.add_argument("--text", type=str, help="Path to contract text file")
    parser.add_argument("--demo", action="store_true", help="Built-in bad vendor contract")
    parser.add_argument("--health", action="store_true", help="Show API/config status")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show redlines + details")
    parser.add_argument("--json", action="store_true", help="Print raw JSON only")
    args = parser.parse_args()

    if args.health:
        _print_health()
        return 0

    if not (args.demo or args.text or args.pdf):
        parser.print_help()
        print("\nQuick tests:")
        print("  python cli.py --health")
        print("  python cli.py --demo")
        print("  python cli.py --demo -v")
        return 1

    from services.workflow import run_workflow

    if args.demo:
        from main import SAMPLE_CONTRACT
        state = {
            "contract_text": SAMPLE_CONTRACT,
            "source_filename": "demo_vendor_agreement.txt",
            "input_type": "text",
            "trigger": "text_upload",
            "sse_events": [],
            "errors": [],
        }
    elif args.text:
        text = Path(args.text).read_text(encoding="utf-8")
        state = {
            "contract_text": text,
            "source_filename": Path(args.text).name,
            "input_type": "text",
            "trigger": "manual_upload",
            "sse_events": [],
            "errors": [],
        }
    else:
        state = {
            "pdf_path": str(Path(args.pdf).resolve()),
            "source_filename": Path(args.pdf).name,
            "input_type": "pdf",
            "trigger": "manual_upload",
            "sse_events": [],
            "errors": [],
        }

    print("\nRunning Spectre pipeline...")
    final = await run_workflow(state)

    if args.json:
        print(json.dumps({
            "contract_id": final.get("contract_id"),
            "phase": final.get("phase"),
            "risk_report": final.get("risk_report"),
            "redline_diff": final.get("redline_diff"),
            "reporter_payload": final.get("reporter_payload"),
            "errors": final.get("errors"),
            "side_effects": final.get("side_effects"),
        }, indent=2))
    else:
        _print_results(final, args.verbose)

    return 0 if final.get("phase") == "complete" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
