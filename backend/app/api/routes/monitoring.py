"""Monitoring lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import MonitoringSession
from app.schemas.monitoring import (
    MonitoringSessionDetail,
    MonitoringSessionOut,
    MonitoringStartRequest,
    MonitoringStopResponse,
)
from app.services.errors import NetPulseError
from app.services.monitoring_service import build_session_payload, monitoring_manager

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("", response_model=list[MonitoringSessionOut])
def list_sessions(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = select(MonitoringSession).order_by(MonitoringSession.started_at.desc()).limit(limit)
    if status:
        query = query.where(MonitoringSession.status == status)
    sessions = db.scalars(query).all()
    return [build_session_payload(db, session) for session in sessions]


@router.post("/start", response_model=MonitoringSessionOut)
async def start_monitoring(
    payload: MonitoringStartRequest, db: Session = Depends(get_db)
) -> dict:
    session = await monitoring_manager.start(db, payload.device_ids, payload.interval_seconds)
    return build_session_payload(db, session)


@router.post("/{session_id}/stop", response_model=MonitoringStopResponse)
def stop_monitoring(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = monitoring_manager.stop(db, session_id)
    return {
        "session_id": session.id,
        "status": session.status,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
    }


@router.get("/{session_id}", response_model=MonitoringSessionDetail)
def session_detail(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = db.get(MonitoringSession, session_id)
    if session is None:
        raise NetPulseError(
            "MONITORING_SESSION_NOT_FOUND",
            f"Monitoring session {session_id} was not found.",
            status_code=404,
        )
    return build_session_payload(db, session, include_observations=True)
