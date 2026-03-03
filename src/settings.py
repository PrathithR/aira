"""
AIRA — Application Settings

Secrets and per-machine config are loaded from .env.
Application behavior defaults are defined here.
Any setting here can be overridden via .env if needed
(e.g. drop LLM_TEMPERATURE=0.5 into .env to experiment).
"""

from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # don't crash on unrelated env vars
    )

    # ==========================================================
    # Environment
    # ==========================================================
    app_env: str = "dev"

    # ==========================================================
    # LLM — Provider & Model
    # ==========================================================
    llm_provider: str = "gemini"
    llm_model: str = "gemini/gemini-2.0-flash"

    # API keys (loaded from .env)
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # ==========================================================
    # LLM — Runtime Tuning
    # ==========================================================
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    # ==========================================================
    # Agent Behavior
    # ==========================================================
    max_tool_iterations: int = 10
    conversation_history_limit: int = 20

    # ==========================================================
    # Local Ollama
    # ==========================================================
    ollama_base_url: str = "http://localhost:11434"

    # ==========================================================
    # Google OAuth (loaded from .env)
    # ==========================================================
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/callback"

    # ==========================================================
    # Encryption (loaded from .env)
    # ==========================================================
    encryption_key: str = ""

    # ==========================================================
    # Database
    # ==========================================================
    database_url: str = "sqlite+aiosqlite:///./data/aira.db"
    db_echo: bool = False  # set DB_ECHO=true in .env to see SQL logs
    
    # ==========================================================
    # Notifications
    # ==========================================================
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = ""
    ntfy_default_priority: str = "default"

    # ==========================================================
    # Scheduler
    # ==========================================================
    default_timezone: str = "America/New_York"
    scheduler_misfire_grace_seconds: int = 30

    # ==========================================================
    # Logging — Derived from APP_ENV, not set manually
    # ==========================================================
    # Override these via .env only if you have a specific reason.
    log_tool_calls: bool = True
    log_llm_responses: bool = False

    @cached_property
    def log_level(self) -> str:
        """
        Derived from APP_ENV:
          dev        → DEBUG
          production → WARNING

        To force a specific level, set LOG_LEVEL_OVERRIDE in .env.
        """
        override = self._get_log_level_override()
        if override:
            return override.upper()

        levels = {
            "dev": "DEBUG",
            "production": "WARNING",
        }
        return levels.get(self.app_env, "DEBUG")

    def _get_log_level_override(self) -> str | None:
        """Check for manual override — escape hatch for edge cases."""
        import os

        return os.getenv("LOG_LEVEL_OVERRIDE")

    # ==========================================================
    # Safety — Hardcoded, NOT configurable
    # ==========================================================
    # These are architectural invariants from Phase 0, not toggles.
    # They exist here for code to reference, not for users to change.

    @property
    def require_confirmation_for_writes(self) -> bool:
        return True

    @property
    def allow_autonomous_writes(self) -> bool:
        return False

    # ==========================================================
    # Convenience
    # ==========================================================
    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @cached_property
    def active_api_key(self) -> str:
        """Return the API key for the currently selected provider."""
        # Ollama runs locally, no API key needed
        if self.llm_provider == "ollama":
            return ""

        keys = {
            "gemini": self.gemini_api_key,
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
        }
        key = keys.get(self.llm_provider, "")
        if not key:
            raise ValueError(
                f"No API key found for provider '{self.llm_provider}'. "
                f"Set the corresponding key in .env."
            )
        return key


# Singleton — import this everywhere
settings = Settings()
