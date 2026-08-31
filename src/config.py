"""Configuration settings for Paper2Patent ADK Agent."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application and ADK agent configuration."""

    # Google GenAI / Gemini API
    GEMINI_API_KEY: Optional[str] = None
    
    # Google Cloud Vertex AI
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_CLOUD_LOCATION: str = "us-central1"
    
    # Model Configurations
    MODEL_NAME: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"
    FALLBACK_TO_MOCK: bool = True
    
    # Server & UI
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    STREAMLIT_PORT: int = 8501
    
    # Observability & Tracing
    LOG_LEVEL: str = "INFO"
    ENABLE_OTEL_TRACING: bool = True
    TRACES_LOG_PATH: str = "logs/traces.jsonl"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings singleton
settings = Settings()
