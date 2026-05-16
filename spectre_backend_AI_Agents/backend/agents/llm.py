"""
Google Gemini (AI Studio) — sole LLM for Spectre.

Set GEMINI_API_KEY from https://aistudio.google.com/apikey
Optional: SPECTRE_GEMINI_MODEL (default gemini-1.5-pro)

Set SPECTRE_LLM_PROVIDER=none to use heuristic-only (no API calls).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

from config import GEMINI_API_KEY, GEMINI_MODEL, LLM_MAX_RETRIES, LLM_RETRY_DELAY_SEC

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def get_provider() -> str:
    explicit = os.getenv("SPECTRE_LLM_PROVIDER", "").lower().strip()
    if explicit == "none":
        return "none"
    if GEMINI_API_KEY:
        return "gemini"
    if explicit == "gemini":
        return "gemini"
    return "none"


def load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parent.parent / "prompts" / f"{name}.xml"
    return path.read_text(encoding="utf-8")


def extract_xml_from_response(text: str, root_tag: str) -> str:
    """Strip markdown fences and isolate XML root (Gemini often adds prose)."""
    cleaned = text.strip()
    fence = re.search(r"```(?:xml)?\s*([\s\S]*?)```", cleaned, re.I)
    if fence:
        cleaned = fence.group(1).strip()
    start = cleaned.find(f"<{root_tag}")
    if start == -1:
        return cleaned
    end = cleaned.rfind(f"</{root_tag}>")
    if end != -1:
        return cleaned[start : end + len(f"</{root_tag}>") + 1]
    return cleaned[start:]


async def _gemini_generate(
    system_prompt: str,
    user_text: str,
    *,
    model: str | None = None,
) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Get a key at https://aistudio.google.com/apikey"
        )

    model_id = model or GEMINI_MODEL
    url = f"{GEMINI_API_BASE}/models/{model_id}:generateContent"

    body = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        },
    }

    last_err: Exception | None = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                r = await client.post(
                    url,
                    params={"key": GEMINI_API_KEY},
                    json=body,
                )
            if r.status_code == 429:
                wait = LLM_RETRY_DELAY_SEC * (2**attempt)
                await asyncio.sleep(wait)
                continue
            if r.status_code == 400:
                err = r.json()
                raise RuntimeError(f"Gemini bad request ({model_id}): {err}")
            if r.status_code == 403:
                raise RuntimeError(
                    "Gemini API key invalid or model not enabled for your project."
                )
            r.raise_for_status()
            data = r.json()

            candidates = data.get("candidates") or []
            if not candidates:
                raise ValueError(f"Gemini returned no candidates: {data}")

            parts = candidates[0].get("content", {}).get("parts") or []
            texts = [p.get("text", "") for p in parts if p.get("text")]
            if not texts:
                finish = candidates[0].get("finishReason", "UNKNOWN")
                raise ValueError(f"Gemini empty text (finishReason={finish})")
            return "\n".join(texts)

        except httpx.HTTPStatusError as e:
            last_err = e
            if e.response.status_code in (500, 502, 503):
                await asyncio.sleep(LLM_RETRY_DELAY_SEC * (2**attempt))
                continue
            raise
        except Exception as e:
            last_err = e
            if attempt < LLM_MAX_RETRIES - 1:
                await asyncio.sleep(LLM_RETRY_DELAY_SEC * (2**attempt))
                continue
            raise

    raise RuntimeError(f"Gemini failed after {LLM_MAX_RETRIES} retries: {last_err}")


async def complete_xml(
    system_prompt: str,
    user_payload: dict[str, Any],
    *,
    model: str | None = None,
    xml_root: str = "risk_report",
) -> str:
    """Structured XML via Gemini — output cleaned for ElementTree parsers."""
    if get_provider() != "gemini":
        raise RuntimeError(
            "Gemini not configured. Set GEMINI_API_KEY or SPECTRE_LLM_PROVIDER=none."
        )

    user_text = (
        "Respond with ONLY valid XML. No markdown, no explanation outside XML.\n\n"
        + json.dumps(user_payload, ensure_ascii=False, indent=2)
    )
    raw = await _gemini_generate(system_prompt, user_text, model=model)
    return extract_xml_from_response(raw, xml_root)


def llm_available() -> bool:
    return get_provider() == "gemini"
