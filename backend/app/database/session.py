"""Database engine, session factory and FastAPI dependency."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.database.base import Base

logger = logging.getLogger(__name__)


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
    pool_pre_ping=True,
    future=True,
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """Enable foreign-key enforcement on SQLite connections."""
    if settings.database_url.startswith("sqlite"):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:  # pragma: no cover - non-SQLite drivers
            logger.debug("Could not set SQLite foreign_keys pragma", exc_info=True)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create all tables that do not exist yet.

    For this single-user academic project SQLAlchemy metadata creation is the
    documented migration strategy.  Use Alembic if the schema evolves.
    """
    # Importing the models registers them on Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised at %s", settings.database_url)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
