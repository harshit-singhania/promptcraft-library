# app/config.py
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/llm_workflow"

    # JWT / Auth
    SECRET_KEY: str = "change-me-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Providers
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE: Optional[str] = "https://openrouter.ai/api/v1"
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None

    # Default Models
    DEFAULT_MODEL: str = "openai/chatgpt-4o-latest"

    # S3
    S3_BUCKET: Optional[str] = None
    S3_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None

    # Local flags
    LOCAL_FAISS: bool = False
    HOST: str = "localhost"
    PORT: int = 8000

    # pydantic-settings v2 config (preferred)
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
        "case_sensitive": False,
    }


# single settings instance used throughout the app
settings = Settings()