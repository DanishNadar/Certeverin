import os
import tempfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Vercel and other serverless hosts mount the deployment read-only. /tmp is the
# only writable location, and it is per-instance and ephemeral.
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
DEFAULT_REPORTS_DIR = (
    Path(tempfile.gettempdir()) / "certeverin-reports" if IS_SERVERLESS else BACKEND_DIR / "generated_reports"
)

# Query parameters some managed Postgres providers append to connection strings
# that libpq/psycopg does not understand.
UNSUPPORTED_PG_PARAMS = {"pgbouncer", "supa", "sslaccept", "schema"}


def normalize_database_url(url: str) -> str:
    """Coerce provider-issued Postgres URLs into a psycopg3 SQLAlchemy URL."""
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    if not url.startswith("postgresql+psycopg://"):
        return url
    parts = urlsplit(url)
    params = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in UNSUPPORTED_PG_PARAMS]
    if not any(key == "sslmode" for key, _ in params):
        params.append(("sslmode", "require"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))


class Settings(BaseSettings):
    app_name: str = "Certeverin"
    database_url: str = "sqlite:///./certeverin.db"
    # Managed Postgres integrations (Vercel/Neon/Supabase) inject these names.
    postgres_url: str | None = None
    postgres_prisma_url: str | None = None
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    usa_jobs_email: str | None = None
    usa_jobs_api_key: str | None = None
    greenhouse_board_slugs: str | None = None
    greenhouse_board_slugs_file: str | None = None
    greenhouse_board_tokens: str | None = None
    lever_company_names: str | None = None
    lever_company_names_file: str | None = None
    # Comma-separated browser origins allowed to call the API cross-origin. The
    # deployed dashboard is same-origin, so this only matters for split hosting.
    allowed_origins: str | None = None
    shared_dir: Path = ROOT_DIR / "shared"
    reports_dir: Path = DEFAULT_REPORTS_DIR
    # Set when the deployment fell back to a throwaway SQLite file because no
    # Postgres DATABASE_URL was configured. Surfaced by /api/health.
    ephemeral_database: bool = False

    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origins(self) -> list[str]:
        defaults = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ]
        extra = [origin.strip() for origin in (self.allowed_origins or "").split(",") if origin.strip()]
        vercel_url = os.getenv("VERCEL_URL")
        if vercel_url:
            extra.append(f"https://{vercel_url}")
        return list(dict.fromkeys(defaults + extra))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.greenhouse_board_slugs and settings.greenhouse_board_tokens:
        settings.greenhouse_board_slugs = settings.greenhouse_board_tokens
    if settings.is_sqlite and (settings.postgres_url or settings.postgres_prisma_url):
        settings.database_url = settings.postgres_url or settings.postgres_prisma_url or settings.database_url
    settings.database_url = normalize_database_url(settings.database_url)
    if IS_SERVERLESS and settings.is_sqlite:
        # The bundle is read-only, so a relative SQLite path cannot be opened.
        # Fall back to a per-instance file so the deployment still boots.
        settings.database_url = f"sqlite:///{Path(tempfile.gettempdir()) / 'certeverin.db'}"
        settings.ephemeral_database = True
    try:
        settings.reports_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Read-only filesystem: reports are generated in memory and stored in the
        # database instead of on disk.
        pass
    return settings
