"""
Central configuration for the backend.

WHAT IS THIS?
Instead of writing secrets (like database keys) directly inside our code,
we keep them in environment variables. An "environment variable" is just a
named value that lives outside the code, e.g. SUPABASE_URL=https://...

WHY?
1. Secrets never get committed to GitHub.
2. We can use different values locally and in production without editing code.

HOW?
We use pydantic-settings. It reads the .env file (during local development)
or the real environment variables (in production) and turns them into a
normal Python object we can import anywhere:

    from app.core.config import settings
    print(settings.APP_NAME)
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration values for the backend, in one place."""

    # ---- Application ----------------------------------------------------
    APP_NAME: str = "MPLADS Backend"
    APP_VERSION: str = "0.1.0"
    # "development" locally, "production" on a real server.
    ENVIRONMENT: str = "development"
    # When True, FastAPI shows extra detail. Must be False in production.
    DEBUG: bool = True
    # How much detail to log: DEBUG, INFO, WARNING, ERROR.
    LOG_LEVEL: str = "INFO"

    # ---- API ------------------------------------------------------------
    # Every endpoint lives under this prefix, e.g. /api/v1/users/me
    API_V1_PREFIX: str = "/api/v1"

    # ---- CORS -----------------------------------------------------------
    # CORS = which website addresses are allowed to call this API from a
    # browser. Comma-separated list, e.g. "http://localhost:3000,https://x.com"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080,http://127.0.0.1:8080"

    # ---- Supabase (used from Stage 3 onwards) ---------------------------
    # Left empty on purpose so the app can still start before Supabase is set
    # up. Stage 3 will add a check that reports whether they are filled in.
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignore any extra variables in .env we have not declared here.
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Turn the comma-separated CORS string into a real Python list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Build the Settings object once and reuse it (that is what lru_cache does).
    Reading the .env file on every request would be slow and pointless.
    """
    return Settings()


# Import this everywhere instead of calling get_settings() by hand.
settings = get_settings()
