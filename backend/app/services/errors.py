"""Domain errors that map to structured API responses."""

from __future__ import annotations

from typing import Any


class NetPulseError(Exception):
    """An expected, user-facing failure."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
