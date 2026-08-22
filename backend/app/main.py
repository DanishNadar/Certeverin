from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import IS_SERVERLESS, get_settings
from app.db.session import bootstrap_database


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Certeverin API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    if not IS_SERVERLESS:
        # Long-lived servers can pay the schema/seed cost once at boot. On
        # serverless it runs lazily on the first request that touches the
        # database, so cold starts stay fast and import never blocks on the network.
        bootstrap_database()

    @app.get("/health")
    def health():
        return health_payload()

    return app


def health_payload() -> dict:
    settings = get_settings()
    payload = {
        "status": "ok",
        "database": "sqlite" if settings.is_sqlite else "postgres",
        "serverless": IS_SERVERLESS,
    }
    if settings.ephemeral_database:
        payload["warning"] = (
            "No Postgres DATABASE_URL is set, so this deployment is using a throwaway SQLite file "
            "that is wiped whenever the instance recycles. Set DATABASE_URL to a Postgres connection string."
        )
    return payload


app = create_app()
