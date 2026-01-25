"""
Application configuration with provider-agnostic LLM setup.

The triage brain is provider-agnostic; swap Gemini/OpenRouter via config.
"""
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # -------------------------------------------------------------------------
    # LLM Provider Configuration
    # -------------------------------------------------------------------------
    llm_provider: Literal["gemini", "openrouter"] = "openrouter"
    google_api_key: str | None = None
    openrouter_api_key: str | None = None
    
    # Model selection
    gemini_model: str = "gemini-2.5-flash"
    openrouter_model: str = "openai/gpt-5.2"
    
    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/triage_alerts"
    
    # -------------------------------------------------------------------------
    # Langfuse Observability
    # -------------------------------------------------------------------------
    langfuse_secret_key: str | None = None
    langfuse_public_key: str | None = None
    langfuse_host: str = "https://us.cloud.langfuse.com"
    
    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    debug: bool = False
    log_level: str = "INFO"
    
    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse is properly configured."""
        return bool(self.langfuse_secret_key and self.langfuse_public_key)


# Global settings instance
settings = Settings()
