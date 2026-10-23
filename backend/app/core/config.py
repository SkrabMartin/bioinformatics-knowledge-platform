from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application configuration loaded from BKP-prefixed environment variables."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ".env"),
        env_prefix="BKP_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Bioinformatics Knowledge Platform API"
    environment: str = "development"
    log_level: str = "INFO"
    log_json: bool = False
    database_url: str = "postgresql+psycopg://bkp:bkp_development@localhost:5432/bkp"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    fixture_path: Path = Path("data/fixtures/phase1_demo.json")
    external_api_timeout_seconds: float = Field(default=15.0, gt=0, le=120)
    external_api_max_attempts: int = Field(default=3, ge=1, le=5)
    external_api_backoff_seconds: float = Field(default=0.5, ge=0, le=10)
    external_api_user_agent: str = "bio-knowledge-platform/0.7.0"
    ncbi_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    ncbi_tool: str = "bio_knowledge_platform"
    ncbi_email: str | None = None
    ncbi_api_key: SecretStr | None = None
    uniprot_base_url: str = "https://rest.uniprot.org"
    admin_api_token: SecretStr | None = None
    graph_timeout_ms: int = Field(default=1500, ge=100, le=10000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
