"""
Application configuration with provider-agnostic LLM setup.

The triage brain is provider-agnostic; swap Gemini/OpenRouter via config.
"""
from typing import Literal, Optional

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
    llm_provider: Literal["gemini", "openrouter", "nvidia"] = "nvidia"
    google_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    # Model selection
    gemini_model: str = "gemini-2.0-flash"
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    
    # -------------------------------------------------------------------------
    # NVIDIA Configuration
    # -------------------------------------------------------------------------
    nvidia_api_key: Optional[str] = None
    nvidia_model: str = "nvidia/llama-3.1-nemotron-70b-instruct"  # Default Nemotron model
    nvidia_nim_endpoint: Optional[str] = None  # For self-hosted NIM containers
    
    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/triage_alerts"
    
    # -------------------------------------------------------------------------
    # Langfuse Observability
    # -------------------------------------------------------------------------
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
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
