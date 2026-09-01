from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI Interviewer API"
    app_env: str = "local"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = Field(description="SQLAlchemy async database URL.")
    redis_url: str = "redis://redis:6379/0"
    jwt_secret_key: SecretStr = Field(description="Secret used to sign access tokens.")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)
    interview_questions_count: int = Field(default=15, gt=0)
    interview_seed_questions_count: int = Field(default=5, gt=0)
    llm_provider: str = "ollama"
    llm_service_url: str = ""
    llm_model: str = "llama3.1:8b"
    llm_timeout_seconds: float = Field(default=60, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_max_tokens: int = Field(default=700, gt=0)
    scoring_fallback_enabled: bool = True
    ml_service_url: str = ""
    ml_timeout_seconds: float = Field(default=3, gt=0)
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated browser origins allowed by CORS.",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return normalized, non-empty CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_interview_question_counts(self) -> "Settings":
        if self.interview_seed_questions_count > self.interview_questions_count:
            raise ValueError("seed question count must not exceed total question count")
        return self


@lru_cache
def get_settings() -> Settings:
    """Create one immutable-by-convention settings instance per process."""
    return Settings()
