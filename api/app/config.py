"""Application configuration."""
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "SDC Form Manager API"
    # SemVer of THIS service (the form-manager runtime). Sourced from the
    # FORM_MANAGER_VERSION env var (set by the Dockerfile build-arg, which is
    # in turn sourced from versions.env at repo root). Falls back to "dev"
    # when running outside the container without the env var set.
    # Decoupled from bundled FHIR content; never hardcode here.
    app_version: str = Field(default="dev", validation_alias="FORM_MANAGER_VERSION")
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
