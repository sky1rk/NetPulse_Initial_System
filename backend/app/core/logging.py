"""Logging configuration for the NetPulse backend."""

from __future__ import annotations

import logging
from logging.config import dictConfig

from app.core.config import settings


def configure_logging() -> None:
    """Configure application logging once at startup."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": settings.log_level.upper(),
                }
            },
            "root": {"handlers": ["console"], "level": settings.log_level.upper()},
            "loggers": {
                "uvicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
                "uvicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configured")
