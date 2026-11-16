"""SQLAlchemy declarative base."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all NetPulse ORM models."""


def utcnow() -> datetime:
    """Return a naive UTC timestamp.

    SQLite does not preserve timezone information reliably, so NetPulse stores
    naive UTC datetimes and appends ``Z`` when serialising to the API.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
