"""
Thin wrapper around Google Gemini API.
Uses gemini-1.5-flash for speed (gemini-1.5-pro as fallback for deep analysis).
"""
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)


_flash_model = None
_pro_model = None


def get_flash() -> genai.GenerativeModel:
    global _flash_model
    if _flash_model is None:
        _flash_model = genai.GenerativeModel("gemini-1.5-flash")
    return _flash_model


def get_pro() -> genai.GenerativeModel:
    global _pro_model
    if _pro_model is None:
        _pro_model = genai.GenerativeModel("gemini-1.5-pro")
    return _pro_model


async def call_gemini(prompt: str, use_pro: bool = False) -> str:
    """
    Call Gemini and return text response.
    use_pro=True for classifier and redline agents (heavier reasoning).
    """
    model = get_pro() if use_pro else get_flash()
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[GEMINI] Error: {e}")
        raise
