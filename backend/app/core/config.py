"""Application configuration loaded from environment / .env file."""

from __future__ import annotations

from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All application settings.

    Values are read from environment variables first; a `.env` file in the
    project root is used as a fallback when running outside Docker.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql://rera_user:rera_pass@localhost:5432/rera_insight"
    )
    ASYNC_DATABASE_URL: str = (
        "postgresql+asyncpg://rera_user:rera_pass@localhost:5432/rera_insight"
    )

    # ── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> List[str]:
        """Accept a comma-separated string, JSON array, or list."""
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    import json
                    return json.loads(v_str)
                except Exception:
                    pass
            return [origin.strip() for origin in v_str.split(",") if origin.strip()]
        return v  # type: ignore[return-value]

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Scraper ───────────────────────────────────────────────────────────────
    SCRAPER_HEADLESS: bool = True
    MAX_WORKERS: int = 4
    TESSERACT_PATH: str = "/usr/bin/tesseract"
    BASE_SEARCH_URL: str = (
        "https://maharera.maharashtra.gov.in/projects-search-result"
    )


# Module-level singleton — import this everywhere.
settings = Settings()
