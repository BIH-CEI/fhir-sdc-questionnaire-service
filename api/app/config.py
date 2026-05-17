"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "SDC Form Manager API"
    # SemVer of THIS service (the form-manager runtime: HAPI image + FastAPI
    # sidecar). Decoupled from the bundled FHIR content version — that lives
    # in Dockerfile.form-manager's PRO_LIBRARY_VERSION and is recorded as a
    # separate Docker label. Runtime and content evolve independently.
    app_version: str = "0.1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"

    # FHIR Server
    fhir_base_url: str = "http://hapi-fhir:8080/fhir"
    fhir_timeout: int = 30

    # CORS
    cors_origins: list[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
