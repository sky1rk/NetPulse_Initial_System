"""System health endpoint."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.database.base import utcnow
from app.database.session import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"
    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": database_status,
        "timestamp": utcnow().isoformat() + "Z",
    }
