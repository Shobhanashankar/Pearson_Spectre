"""
Configuration values for agents module.
These are imported by various agent files.
"""
import os

# Gemini / LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("SPECTRE_GEMINI_MODEL", "gemini-1.5-flash")
LLM_MAX_RETRIES = int(os.getenv("SPECTRE_LLM_MAX_RETRIES", "3"))
LLM_RETRY_DELAY_SEC = float(os.getenv("SPECTRE_LLM_RETRY_DELAY", "2.0"))
LLM_BATCH_SIZE = int(os.getenv("SPECTRE_LLM_BATCH_SIZE", "8"))

# Confidence threshold for risk classification
CONFIDENCE_THRESHOLD = float(os.getenv("SPECTRE_CONFIDENCE_THRESHOLD", "0.72"))

# File upload limits
MAX_UPLOAD_BYTES = int(os.getenv("SPECTRE_MAX_UPLOAD_MB", "25")) * 1024 * 1024
MIN_CLAUSE_CHARS = int(os.getenv("SPECTRE_MIN_CLAUSE_CHARS", "40"))

# Output directory
OUTPUT_DIR = os.getenv("SPECTRE_OUTPUT_DIR", "./output")

# Reflection settings
MAX_GLOBAL_REFLECTION_PASSES = int(os.getenv("SPECTRE_MAX_REFLECTION_PASSES", "10"))

# Side effects
DRY_RUN_SIDE_EFFECTS = os.getenv("SPECTRE_DRY_RUN", "false").lower() == "true"

# GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

# Slack
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Omium
OMIUM_API_KEY = os.getenv("OMIUM_API_KEY", "")
OMIUM_PROJECT_ID = os.getenv("OMIUM_PROJECT_ID", "spectre")
OMIUM_ENABLED = os.getenv("OMIUM_ENABLED", "false").lower() == "true"