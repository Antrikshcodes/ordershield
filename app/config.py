"""OrderShield AI - Configuration Settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    REVIEW_THRESHOLD: float = 0.30
    REJECT_THRESHOLD: float = 0.65
    HIGH_VALUE_THRESHOLD: float = 5000.00

    REGISTRY_BASE_URL: str = "https://api.ordershield-registry.internal"
    REGISTRY_TIMEOUT_SECONDS: float = 4.0

    AGENT_NAME: str = "ordershield_verifier"
    AGENT_PORT: int = 8001
    AGENT_SEED: str = "ordershield_default_seed_phrase_secure_agent"
    AGENT_ENDPOINT: str = "http://127.0.0.1:8001/submit"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()