from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Gemini
    GEMINI_API_KEY: str = ""

    # JWT
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO: Optional[str] = None

    # Slack
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./spectre.db"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    SPECTRE_DB_PATH: str = "./spectre.db"
    SPECTRE_OUTPUT_DIR: str = "./output"
    SPECTRE_MAX_UPLOAD_MB: int = 25
    SPECTRE_MIN_CLAUSE_CHARS: int = 40

    # LLM Configuration
    SPECTRE_GEMINI_MODEL: str = "gemini-1.5-flash"
    SPECTRE_CONFIDENCE_THRESHOLD: float = 0.72
    SPECTRE_LLM_MAX_RETRIES: int = 3
    SPECTRE_LLM_RETRY_DELAY: float = 2.0
    SPECTRE_LLM_BATCH_SIZE: int = 8

    # Workflow Settings
    SPECTRE_DRY_RUN: bool = False
    SPECTRE_MAX_REFLECTION_RETRIES: int = 2
    SPECTRE_MAX_REFLECTION_PASSES: int = 10

    # Tracing & Monitoring
    OMIUM_API_KEY: str = ""
    OMIUM_PROJECT_ID: str = "spectre"
    OMIUM_ENABLED: bool = False
    OMIUM_DASHBOARD_URL: str = "https://www.omium.ai/"

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Frontend Configuration
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
