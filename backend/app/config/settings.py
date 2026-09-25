from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Branding
    APP_NAME: str = "OpenWahi"

    # Firebase Configuration
    FIREBASE_PROJECT_ID: str
    FIREBASE_SERVICE_ACCOUNT_PATH: str = "/run/secrets/firebase-service-account.json"

    # Database Configuration (for SQLAlchemy/Alembic)
    DATABASE_URL: str | None = None

    # FastAPI Configuration
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # WhatsApp Service (GOWA)
    WHATSAPP_USER: str = "admin"
    WHATSAPP_PASSWORD: str = "secret123"
    WHATSAPP_WEBHOOK_SECRET: str = "whatsapp-webhook-secret"

    # Audio transcription microservice
    TRANSCRIBER_URL: str = "http://localhost:8001"

    # AI Assistant Configuration
    AI_ENCRYPTION_KEY: str
    GROQ_API_KEY: Optional[str] = None  # Global Groq API key (optional, users can use their own)
    LLAMACPP_BASE_URL: str = "http://llamacpp:8080/v1"
    LLAMACPP_MODEL: str = "Qwen3.5-0.8B-Q8_0"

    # Qdrant Vector Database Configuration
    QDRANT_URL: Optional[str] = None  # Full HTTPS URL for Qdrant Cloud
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None  # For Qdrant Cloud

    # Storage Configuration (MinIO/S3)
    S3_ENDPOINT_URL: str = "http://localhost:9000"  # MinIO local
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin123"
    S3_BUCKET_NAME: str = "knowledge-files"
    S3_REGION: str = "us-east-1"

    # Embeddings Configuration
    EMBEDDING_PROVIDER: str = "sentence-transformers"  # LOCAL, FREE, RECOMMENDED
    EMBEDDING_MODEL: str = "multi-qa-MiniLM-L6-cos-v1"  # Optimized for Q&A/RAG
    EMBEDDING_DIMENSIONS: int = 384  # MiniLM uses 384 dimensions

    # Optional: API keys for fallback providers
    JINA_API_KEY: Optional[str] = None  # Free tier: 1M tokens/month
    OPENAI_API_KEY: Optional[str] = None  # Paid but high quality

    # Sentry Monitoring
    SENTRY_DSN: Optional[str] = None  # Set to enable error tracking & performance monitoring
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0  # 1.0 = 100% of transactions (reduce in production)
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0  # 1.0 = 100% of profiled transactions

    # Knowledge Base Limits (Optimized for 2-4GB RAM VPS)
    KB_MAX_FILE_SIZE_MB: int = 5  # Max 5MB per file (conservative for small VPS)
    KB_MAX_BASES_PER_USER: int = 3  # Max 3 knowledge bases per user
    KB_MAX_DOCS_PER_BASE: int = 30  # Max 30 documents per knowledge base

    # Managed AI — Pro plan
    MANAGED_AI_PROVIDER: str = "llamacpp"
    MANAGED_AI_MODEL: str = "Qwen3.5-0.8B-Q8_0"
    # Local CPU inference does not reliably emit tool calls, so managed agent
    # runs that need tools escalate to this provider instead.
    MANAGED_AI_TOOL_ESCALATION_ENABLED: bool = True
    MANAGED_AI_TOOL_PROVIDER: str = "groq"
    MANAGED_AI_TOOL_MODEL: str = "llama-3.3-70b-versatile"
    OPENCODE_GO_API_KEY: Optional[str] = None
    BEDROCK_API_KEY: Optional[str] = None  # Bedrock direct API key (re:Invent 2024)
    PRO_MONTHLY_CONVERSATION_LIMIT: int = 3000

    # Admin dashboard: comma-separated emails; empty disables the admin API.
    ADMIN_EMAILS: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated ALLOWED_ORIGINS to list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def admin_emails_set(self) -> set[str]:
        """Lowercased admin emails parsed from comma-separated ADMIN_EMAILS."""
        return {
            email.strip().lower() for email in self.ADMIN_EMAILS.split(",") if email.strip()
        }

    @property
    def get_database_url(self) -> str:
        """
        Get database URL for SQLAlchemy/Alembic.
        Requires DATABASE_URL to be set explicitly in environment variables.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        raise ValueError("DATABASE_URL must be set in environment variables.")


# Global settings instance
settings = Settings()
