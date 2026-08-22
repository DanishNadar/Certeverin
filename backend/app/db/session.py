import threading

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import IS_SERVERLESS, get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine_kwargs: dict = {"connect_args": connect_args, "pool_pre_ping": True}
if IS_SERVERLESS and not settings.is_sqlite:
    # Serverless instances are frozen between invocations, so a pooled connection
    # is usually dead by the time the instance is reused. Open per request and
    # let the provider's connection pooler do the pooling.
    engine_kwargs = {"connect_args": connect_args, "poolclass": NullPool}
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_bootstrap_lock = threading.Lock()
_bootstrapped = False


def init_db() -> None:
    from app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)


def _schema_exists() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM certifications LIMIT 1"))
        return True
    except SQLAlchemyError:
        return False


def _add_missing_columns() -> None:
    """Tiny forward migration for databases created before a column was added.

    Base.metadata.create_all only creates missing tables, never missing columns.
    """
    additions = {"report_exports": {"content": "BLOB" if settings.is_sqlite else "BYTEA"}}
    inspector = inspect(engine)
    for table, columns in additions.items():
        if not inspector.has_table(table):
            continue
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, column_type in columns.items():
            if name in existing:
                continue
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"))


def bootstrap_database(force: bool = False) -> None:
    """Create tables and load seed data once per process.

    Serverless instances start cold, so this has to be cheap on the happy path:
    one probe query when the schema is already there.
    """
    global _bootstrapped
    if _bootstrapped and not force:
        return
    with _bootstrap_lock:
        if _bootstrapped and not force:
            return
        from app.services.seeds import seed_all

        if force or not _schema_exists():
            init_db()
        _add_missing_columns()
        with SessionLocal() as db:
            seed_all(db, force=force)
        _bootstrapped = True


def get_db():
    bootstrap_database()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
