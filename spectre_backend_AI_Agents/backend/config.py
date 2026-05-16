"""Spectre configuration — env-driven for enterprise deploys."""

from __future__ import annotations

import os
from pathlib import Path

# Load .env from backend/ if present
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv

        load_dotenv(_env_file)
    except ImportError:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = Path(os.getenv("SPECTRE_UPLOAD_DIR", str(BASE_DIR / "uploads")))
DB_PATH = Path(os.getenv("SPECTRE_DB_PATH", str(BASE_DIR / "spectre.db")))
OUTPUT_DIR = Path(os.getenv("SPECTRE_OUTPUT_DIR", str(BASE_DIR / "output")))

MAX_UPLOAD_BYTES = int(os.getenv("SPECTRE_MAX_UPLOAD_MB", "25")) * 1024 * 1024
CONFIDENCE_THRESHOLD = float(os.getenv("SPECTRE_CONFIDENCE_THRESHOLD", "0.72"))
MAX_REFLECTION_RETRIES = int(os.getenv("SPECTRE_MAX_REFLECTION_RETRIES", "2"))
MAX_GLOBAL_REFLECTION_PASSES = int(os.getenv("SPECTRE_MAX_REFLECTION_PASSES", "10"))
LLM_BATCH_SIZE = int(os.getenv("SPECTRE_LLM_BATCH_SIZE", "8"))
MIN_CLAUSE_CHARS = int(os.getenv("SPECTRE_MIN_CLAUSE_CHARS", "40"))

# Google Gemini (AI Studio) — https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv(
    "SPECTRE_GEMINI_MODEL",
    os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
)
LLM_MAX_RETRIES = int(os.getenv("SPECTRE_LLM_MAX_RETRIES", "3"))
LLM_RETRY_DELAY_SEC = float(os.getenv("SPECTRE_LLM_RETRY_DELAY", "2.0"))

# Omium tracing — https://omium.dev (hackathon +10% bonus)
OMIUM_API_KEY = os.getenv("OMIUM_API_KEY", "")
OMIUM_PROJECT_ID = os.getenv("OMIUM_PROJECT_ID", "spectre")
OMIUM_ENABLED = os.getenv("OMIUM_ENABLED", "true").lower() in ("1", "true", "yes")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # owner/name
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
DRY_RUN_SIDE_EFFECTS = os.getenv("SPECTRE_DRY_RUN", "true").lower() in ("1", "true", "yes")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
