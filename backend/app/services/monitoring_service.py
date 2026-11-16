"""Periodic device monitoring lifecycle.

Each running session has one bounded asyncio task.  Tasks are stopped cleanly,
observations are timestamped, and sessions left running by a previous backend
process are marked ``interrupted`` instead of being resumed silently.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.database.session import SessionLocal
from app.models import Device, MonitoringObservation, MonitoringSession, MonitoringSessionDevice
from app.services.connectivity_service import PingUtilityUnavailable, ping_once
from app.services.errors import NetPulseError
from app.services.ws_manager import manager

logger = logging.getLogger(__name__)


class MonitoringManager:
    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task] = {}
        self._stop_events: dict[int, asyncio.Event] = {}

    async def start(
        self, db: Session, device_ids: list[int], interval_seconds: int
    ) -> MonitoringSession:
        if (
            interval_seconds < settings.monitoring_min_interval_seconds
            or interval_seconds > settings.monitoring_max_interval_seconds
        ):
            raise NetPulseError(
                "INVALID_MONITORING_INTERVAL",
                (
                    "Interval must be between "
                    f"{settings.monitoring_min_interval_seconds} and "
                    f"{settings.monitoring_max_interval_seconds} seconds."
                ),
                status_code=422,
            )

        unique_ids = list(dict.fromkeys(device_ids))
        devices = db.scalars(select(Device).where(Device.id.in_(unique_ids))).all()
        found_ids = {device.id for device in devices}
        missing = [device_id for device_id in unique_ids if device_id not in found_ids]
        if missing:
            raise NetPulseError(
                "DEVICE_NOT_FOUND",
                f"Device(s) not found: {', '.join(str(value) for value in missing)}.",
                status_code=404,
            )

        active = db.scalars(
            select(MonitoringSession)
            .join(MonitoringSessionDevice, MonitoringSession.id == MonitoringSessionDevice.session_id)
            .where(
                MonitoringSession.status == "running",
                MonitoringSessionDevice.device_id.in_(unique_ids),
            )
        ).all()
        if active:
            raise NetPulseError(
                "MONITORING_ALREADY_ACTIVE",
                "One or more selected devices are already in a running monitoring session.",
                status_code=409,
            )

        session = MonitoringSession(
            started_at=utcnow(),
            interval_seconds=interval_seconds,
            status="running",
        )
        db.add(session)
        db.flush()
        for device_id in unique_ids:
            db.add(MonitoringSessionDevice(session_id=session.id, device_id=device_id))
        db.commit()
        db.refresh(session)

        stop_event = asyncio.Event()
        self._stop_events[session.id] = stop_event
        self._tasks[session.id] = asyncio.create_task(
            self._run_session(session.id, unique_ids, interval_seconds, stop_event)
        )
        logger.info("Monitoring session %s started for devices %s", session.id, unique_ids)
        return session

    async def _run_session(
        self,
        session_id: int,
        device_ids: list[int],
        interval_seconds: int,
        stop_event: asyncio.Event,
    ) -> None:
        try:
            while not stop_event.is_set():
                events: list[dict] = []
                with SessionLocal() as db:
                    session = db.get(MonitoringSession, session_id)
                    if session is None or session.status != "running":
                        break
                    for device_id in device_ids:
                        if stop_event.is_set():
                            break
                        device = db.get(Device, device_id)
                        if device is None:
                            continue
                        observed_at = utcnow()
                        icmp_success = False
                        error_message: str | None = None
                        try:
                            result = await asyncio.to_thread(
                                ping_once, device.ip_address, settings.ping_default_timeout_ms
                            )
                            icmp_success = result.success
                            observation = "responding" if result.success else "no_icmp_response"
                            latency = result.latency_ms if result.success else None
                            error_message = None if result.success else result.error_message
                        except PingUtilityUnavailable as exc:
                            observation = "error"
                            latency = None
                            error_message = str(exc)
                        except Exception as exc:  # pragma: no cover - defensive
                            logger.warning("Monitoring probe failed for %s: %s", device.ip_address, exc)
                            observation = "error"
                            latency = None
                            error_message = "Unexpected monitoring probe failure."

                        if stop_event.is_set():
                            break

                        record = MonitoringObservation(
                            session_id=session_id,
                            device_id=device_id,
                            observed_at=observed_at,
                            icmp_success=icmp_success,
                            latency_ms=latency,
                            observation=observation,
                        )
                        db.add(record)
                        if observation == "responding":
                            device.last_seen = observed_at
                        if observation == "error" and error_message:
                            session.error_message = error_message
                        db.flush()
                        events.append(
                            {
                                "event": "monitoring.observation",
                                "session_id": session_id,
                                "device_id": device_id,
                                "ip_address": device.ip_address,
                                "observed_at": observed_at.isoformat() + "Z",
                                "icmp_success": record.icmp_success,
                                "latency_ms": latency,
                                "observation": observation,
                            }
                        )
                    db.commit()

                for payload in events:
                    await manager.broadcast(payload)

                if stop_event.is_set():
                    break
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            logger.info("Monitoring session %s task cancelled", session_id)
            raise
        except Exception:
            logger.exception("Monitoring session %s failed", session_id)
            with SessionLocal() as db:
                session = db.get(MonitoringSession, session_id)
                if session is not None and session.status == "running":
                    session.status = "failed"
                    session.ended_at = utcnow()
                    session.error_message = "Monitoring task stopped after an unexpected error."
                    db.commit()
            await manager.broadcast(
                {"event": "monitoring.session_failed", "session_id": session_id}
            )
        finally:
            self._tasks.pop(session_id, None)
            self._stop_events.pop(session_id, None)

    def stop(self, db: Session, session_id: int) -> MonitoringSession:
        session = db.get(MonitoringSession, session_id)
        if session is None:
            raise NetPulseError(
                "MONITORING_SESSION_NOT_FOUND",
                f"Monitoring session {session_id} was not found.",
                status_code=404,
            )
        if session.status == "running":
            session.status = "stopped"
            session.ended_at = utcnow()
            db.commit()
            db.refresh(session)
        event = self._stop_events.get(session_id)
        if event is not None:
            event.set()
        return session

    async def shutdown(self) -> None:
        for event in list(self._stop_events.values()):
            event.set()
        tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._stop_events.clear()

    def mark_stale_sessions(self, db: Session) -> int:
        """Mark sessions left running by a previous process as interrupted."""
        stale = db.scalars(
            select(MonitoringSession).where(MonitoringSession.status == "running")
        ).all()
        for session in stale:
            session.status = "interrupted"
            session.ended_at = utcnow()
            session.error_message = "Backend restarted before the session was stopped."
        if stale:
            db.commit()
            logger.warning("Marked %s stale monitoring session(s) as interrupted", len(stale))
        return len(stale)


monitoring_manager = MonitoringManager()


def session_observations(db: Session, session_id: int) -> list[MonitoringObservation]:
    return list(
        db.scalars(
            select(MonitoringObservation)
            .where(MonitoringObservation.session_id == session_id)
            .order_by(MonitoringObservation.observed_at.asc())
        ).all()
    )


def build_session_payload(
    db: Session,
    session: MonitoringSession,
    include_observations: bool = False,
) -> dict:
    observations = session_observations(db, session.id)
    success_count = len([observation for observation in observations if observation.icmp_success])
    availability = (
        round(success_count / len(observations) * 100, 2) if observations else None
    )
    payload = {
        "session_id": session.id,
        "status": session.status,
        "interval_seconds": session.interval_seconds,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "device_ids": [link.device_id for link in session.device_links],
        "observation_count": len(observations),
        "success_count": success_count,
        "failure_count": len(observations) - success_count,
        "availability_percent": availability,
        "latest_observation_at": observations[-1].observed_at if observations else None,
    }
    if include_observations:
        payload["observations"] = observations
    return payload


def cleanup_timestamp(value: datetime | None) -> datetime | None:
    return value
