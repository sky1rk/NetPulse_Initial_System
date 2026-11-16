"""Monitoring lifecycle safety tests (no real probes are sent)."""

from __future__ import annotations

import asyncio

import pytest

from app.database.base import utcnow
from app.models import MonitoringSession, MonitoringSessionDevice
from app.services import monitoring_service


def test_stale_running_sessions_are_interrupted(db_session):
    session = MonitoringSession(started_at=utcnow(), interval_seconds=10, status="running")
    db_session.add(session)
    db_session.commit()

    count = monitoring_service.monitoring_manager.mark_stale_sessions(db_session)
    db_session.refresh(session)
    assert count == 1
    assert session.status == "interrupted"
    assert session.ended_at is not None
    assert "restarted" in (session.error_message or "").lower()


def test_interval_bounds_enforced(db_session, device):
    manager = monitoring_service.MonitoringManager()
    with pytest.raises(Exception) as error:
        asyncio.run(manager.start(db_session, [device.id], 1))
    assert getattr(error.value, "code", "") == "INVALID_MONITORING_INTERVAL"


def test_duplicate_active_device_rejected(db_session, device):
    session = MonitoringSession(started_at=utcnow(), interval_seconds=10, status="running")
    db_session.add(session)
    db_session.flush()
    db_session.add(MonitoringSessionDevice(session_id=session.id, device_id=device.id))
    db_session.commit()

    manager = monitoring_service.MonitoringManager()
    with pytest.raises(Exception) as error:
        asyncio.run(manager.start(db_session, [device.id], 10))
    assert getattr(error.value, "code", "") == "MONITORING_ALREADY_ACTIVE"


def test_unknown_device_rejected(db_session):
    manager = monitoring_service.MonitoringManager()
    with pytest.raises(Exception) as error:
        asyncio.run(manager.start(db_session, [999], 10))
    assert getattr(error.value, "code", "") == "DEVICE_NOT_FOUND"


def test_stop_unknown_session_rejected(db_session):
    manager = monitoring_service.MonitoringManager()
    with pytest.raises(Exception) as error:
        manager.stop(db_session, 999)
    assert getattr(error.value, "code", "") == "MONITORING_SESSION_NOT_FOUND"
