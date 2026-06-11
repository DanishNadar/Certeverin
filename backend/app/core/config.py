from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Certeverin"
    database_url: str = "sqlite:///./certeverin.db"
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    usa_jobs_email: str | None = None
    usa_jobs_api_key: str | None = None
    greenhouse_board_slugs: str | None = None
    greenhouse_board_slugs_file: str | None = None
    greenhouse_board_tokens: str | None = None
    lever_company_names: str | None = None
    lever_company_names_file: str | None = None
    shared_dir: Path = ROOT_DIR / "shared"
    reports_dir: Path = BACKEND_DIR / "generated_reports"

    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.greenhouse_board_slugs and settings.greenhouse_board_tokens:
        settings.greenhouse_board_slugs = settings.greenhouse_board_tokens
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings
