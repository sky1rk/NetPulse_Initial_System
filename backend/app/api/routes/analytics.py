"""Performance analytics endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.analytics import AnalyticsSummary, HistoryResponse
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    device_id: int | None = Query(default=None),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> dict:
    return analytics_service.get_summary(db, device_id=device_id, from_dt=from_date, to_dt=to_date)


@router.get("/history", response_model=HistoryResponse)
def analytics_history(
    device_id: int | None = Query(default=None),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    return analytics_service.get_history(
        db,
        device_id=device_id,
        from_dt=from_date,
        to_dt=to_date,
        limit=limit,
    )
