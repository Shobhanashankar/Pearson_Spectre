"""
Extraction Agent:
  - Opens PDF with pdfplumber
  - Splits into clauses (paragraph-level)
  - Returns a clause manifest (list of dicts)
"""
import io
import pdfplumber
import re
from typing import List, Dict, Any, Union


def extract_clauses(file_source: Union[str, bytes]) -> List[Dict[str, Any]]:
    """
    Extract clauses from a PDF file or PDF bytes.
    Returns a list of clause objects.
    """
    clauses = []
    full_text = ""

    try:
        source = io.BytesIO(file_source) if isinstance(file_source, (bytes, bytearray)) else file_source
        with pdfplumber.open(source) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    full_text += f"\n[PAGE {page_num}]\n{text}"
    except Exception as e:
        raise RuntimeError(f"pdfplumber failed to open PDF: {e}")

    if not full_text.strip():
        raise RuntimeError("PDF has no extractable text (may be scanned image).")

    # Split into paragraphs / clause-like chunks
    paragraphs = re.split(r'\n{2,}', full_text)

    idx = 0
    for para in paragraphs:
        para = para.strip()
        if len(para) < 40:  # skip very short fragments (page headers, etc.)
            continue
        clauses.append({
            "index": idx,
            "text": para,
            "char_count": len(para),
        })
        idx += 1

    print(f"[EXTRACTION] Extracted {len(clauses)} clauses")
    return clauses
