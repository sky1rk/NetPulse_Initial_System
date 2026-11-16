"""Shared schema helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, PlainSerializer


def serialize_utc(value: datetime | None) -> str | None:
    """Serialise naive UTC datetimes with an explicit ``Z`` suffix."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[datetime, PlainSerializer(serialize_utc, return_type=str)]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class MessageResponse(BaseModel):
    message: str
