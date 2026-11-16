"""Diagnostic recommendation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.base import utcnow
from app.database.session import get_db
from app.schemas.diagnostics import RecommendationsResponse
from app.services import diagnostics_service

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/recommendations", response_model=RecommendationsResponse)
def recommendations(
    device_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    items = diagnostics_service.build_recommendations(db, device_id=device_id)
    return {"items": items, "generated_at": utcnow()}
