from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    GROQ_API_KEY: Optional[str] = None
    WHISPER_MODEL: str = "base"  # opciones: tiny, base, small
    GROQ_TIMEOUT_SECONDS: float = 10.0
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"


settings = Settings()
