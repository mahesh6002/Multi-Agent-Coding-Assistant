import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # API Keys
    GOOGLE_API_KEY: str = Field(default="")
    
    # Mock Mode Configuration
    MOCK_LLM: bool = Field(default=True)
    
    # Model Names (Gemini 2.5 Verified)
    MODEL_SUPERVISOR: str = Field(default="gemini-2.5-pro")
    MODEL_PLANNER: str = Field(default="gemini-2.5-flash")
    MODEL_CODER: str = Field(default="gemini-2.5-flash")
    MODEL_REVIEWER: str = Field(default="gemini-2.5-pro")
    MODEL_DEBUGGER: str = Field(default="gemini-2.5-flash")
    MODEL_DOCS: str = Field(default="gemini-2.5-flash")
    
    # Sandbox Settings
    DOCKER_IMAGE: str = Field(default="assistant-sandbox:latest")
    SANDBOX_TIMEOUT: int = Field(default=15)
    SANDBOX_MEMORY_LIMIT: str = Field(default="64m")
    
    # Orchestrator Settings
    MAX_ITERATIONS: int = Field(default=15)
    PORT: int = Field(default=8000)
    
    # Checkpoint DB
    CHECKPOINT_DB_PATH: str = Field(default="checkpoints.db")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
