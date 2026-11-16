"""Performance analytics derived exclusively from persisted observations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.models import (
    Device,
    MonitoringObservation,
    MonitoringSession,
    NetworkScan,
    PingProbe,
    PingTest,
    Report,
    SecurityFinding,
    SecurityScan,
)
from app.services import metrics
from app.services.devices_service import get_device_or_404, latest_observations
from app.services.errors import NetPulseError


def to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def resolve_window(
    from_dt: datetime | None, to_dt: datetime | None
) -> tuple[datetime, datetime]:
    """Validate and normalise an analytics time window."""
    to_value = to_naive_utc(to_dt) or utcnow()
    from_value = to_naive_utc(from_dt) or (to_value - timedelta(hours=settings.analytics_default_window_hours))
    if from_value >= to_value:
        raise NetPulseError(
            "INVALID_TIME_RANGE", "The 'from' timestamp must be earlier than the 'to' timestamp."
        )
    if (to_value - from_value) > timedelta(days=366):
        raise NetPulseError(
            "INVALID_TIME_RANGE", "The requested time range must not exceed 366 days."
        )
    return from_value, to_value


def _collect_points(
    db: Session, window_from: datetime, window_to: datetime, device_id: int | None = None
) -> list[dict]:
    points: list[dict] = []

    probe_query = (
        select(PingProbe, PingTest.device_id)
        .join(PingTest, PingProbe.ping_test_id == PingTest.id)
        .where(
            PingTest.status == "completed",
            PingProbe.tested_at >= window_from,
            PingProbe.tested_at <= window_to,
        )
    )
    if device_id is not None:
        probe_query = probe_query.where(PingTest.device_id == device_id)
    for probe, probe_device_id in db.execute(probe_query).all():
        points.append(
            {
                "timestamp": probe.tested_at,
                "device_id": probe_device_id,
                "latency_ms": probe.latency_ms if probe.success else None,
                "success": bool(probe.success),
                "observation": "responding" if probe.success else "no_icmp_response",
                "source": "ping",
            }
        )

    observation_query = select(MonitoringObservation).where(
        MonitoringObservation.observed_at >= window_from,
        MonitoringObservation.observed_at <= window_to,
    )
    if device_id is not None:
        observation_query = observation_query.where(MonitoringObservation.device_id == device_id)
    for observation in db.scalars(observation_query).all():
        points.append(
            {
                "timestamp": observation.observed_at,
                "device_id": observation.device_id,
                "latency_ms": observation.latency_ms,
                "success": bool(observation.icmp_success),
                "observation": observation.observation,
                "source": "monitoring",
            }
        )

    points.sort(key=lambda point: point["timestamp"])
    return points


def summarize_points(
    points: list[dict],
    window_from: datetime,
    window_to: datetime,
    device_id: int | None = None,
) -> dict:
    sent = len(points)
    successful = [point for point in points if point["success"] and point["latency_ms"] is not None]
    latencies = [float(point["latency_ms"]) for point in successful]
    stats = metrics.latency_statistics(latencies)
    loss = metrics.packet_loss_percent(sent, len(successful))
    jitter = metrics.jitter_ms(latencies)

    monitoring_points = [point for point in points if point["source"] == "monitoring"]
    monitoring_success = [point for point in monitoring_points if point["success"]]
    availability = metrics.availability_percent(len(monitoring_success), len(monitoring_points))

    notes: list[str] = []
    sources = {point["source"] for point in points}
    if len(sources) > 1:
        notes.append(
            "Metrics combine ping-test probes and monitoring observations from the selected window."
        )
    if not monitoring_points:
        notes.append(
            "Availability is unavailable because no monitoring observations exist in this window."
        )
    if not points:
        notes.append("No connectivity observations were recorded in this window.")
    if successful and len(successful) < 2:
        notes.append("Jitter requires at least two successful latency samples.")

    score = metrics.health_score(
        avg_latency_ms=stats["avg_latency_ms"],
        loss_percent=loss,
        availability=availability,
        good_ms=settings.latency_good_ms,
        fair_ms=settings.latency_fair_ms,
        poor_ms=settings.latency_poor_ms,
    )
    if score and not monitoring_points:
        notes.append("The health score is withheld because availability data is missing.")
        score = None

    return {
        "device_id": device_id,
        "window_from": window_from,
        "window_to": window_to,
        "sample_count": sent,
        "successful_samples": len(successful),
        "avg_latency_ms": stats["avg_latency_ms"],
        "min_latency_ms": stats["min_latency_ms"],
        "max_latency_ms": stats["max_latency_ms"],
        "packet_loss_percent": loss,
        "jitter_ms": jitter,
        "observation_count": len(monitoring_points),
        "successful_observations": len(monitoring_success),
        "availability_percent": availability,
        "health_score": score,
        "notes": notes,
    }


def get_summary(
    db: Session,
    device_id: int | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> dict:
    if device_id is not None:
        get_device_or_404(db, device_id)
    window_from, window_to = resolve_window(from_dt, to_dt)
    points = _collect_points(db, window_from, window_to, device_id)
    return summarize_points(points, window_from, window_to, device_id)


def get_history(
    db: Session,
    device_id: int | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    limit: int = 500,
) -> dict:
    if device_id is not None:
        get_device_or_404(db, device_id)
    window_from, window_to = resolve_window(from_dt, to_dt)
    points = _collect_points(db, window_from, window_to, device_id)
    limited = points[-limit:] if limit > 0 else []
    notes: list[str] = []
    if not limited:
        notes.append("No observations exist in this window. Run a ping test or start monitoring.")
    if len(points) > len(limited):
        notes.append(f"Showing the most recent {len(limited)} of {len(points)} observations.")
    return {
        "device_id": device_id,
        "window_from": window_from,
        "window_to": window_to,
        "points": limited,
        "sample_count": len(limited),
        "success_count": len([point for point in limited if point["success"]]),
        "notes": notes,
    }


def _latest_security_scans(db: Session) -> list[SecurityScan]:
    latest = (
        select(SecurityScan.device_id, func.max(SecurityScan.started_at).label("started_at"))
        .where(SecurityScan.status == "completed")
        .group_by(SecurityScan.device_id)
        .subquery()
    )
    return list(
        db.scalars(
            select(SecurityScan).join(
                latest,
                (SecurityScan.device_id == latest.c.device_id)
                & (SecurityScan.started_at == latest.c.started_at),
            )
        ).all()
    )


def get_dashboard_summary(db: Session) -> dict:
    devices = db.scalars(select(Device)).all()
    observations = latest_observations(db, [device.id for device in devices])

    responding = 0
    no_icmp = 0
    not_tested = 0
    latest_times: list[datetime] = []
    for device in devices:
        observation = observations.get(device.id, {})
        status = observation.get("latest_observation", "not_tested")
        if status == "responding":
            responding += 1
        elif status in {"no_icmp_response", "error"}:
            no_icmp += 1
        else:
            not_tested += 1
        observed_at = observation.get("latest_observation_at")
        if observed_at:
            latest_times.append(observed_at)

    window_to = utcnow()
    window_from = window_to - timedelta(hours=settings.analytics_default_window_hours)
    analytics = summarize_points(
        _collect_points(db, window_from, window_to, None), window_from, window_to, None
    )

    last_scan = db.scalar(select(func.max(NetworkScan.completed_at)))
    active_sessions = db.scalar(
        select(func.count(MonitoringSession.id)).where(MonitoringSession.status == "running")
    ) or 0

    open_findings = 0
    for scan in _latest_security_scans(db):
        open_findings += (
            db.scalar(
                select(func.count(SecurityFinding.id)).where(
                    SecurityFinding.security_scan_id == scan.id,
                    SecurityFinding.state == "open",
                )
            )
            or 0
        )

    reports_count = db.scalar(select(func.count(Report.id))) or 0
    activity: list[dict] = []

    for scan in db.scalars(select(NetworkScan).order_by(NetworkScan.started_at.desc()).limit(5)).all():
        activity.append(
            {
                "activity_type": "discovery",
                "title": "Discovery scan",
                "description": f"{scan.discovered_count} host(s) observed in {scan.network_cidr}.",
                "timestamp": scan.completed_at or scan.started_at,
                "status": scan.status,
            }
        )
    for test in db.scalars(select(PingTest).order_by(PingTest.started_at.desc()).limit(5)).all():
        device = db.get(Device, test.device_id)
        loss_text = "N/A" if test.packet_loss_percent is None else f"{test.packet_loss_percent:g}% loss"
        activity.append(
            {
                "activity_type": "connectivity",
                "title": "Ping test",
                "description": f"{device.ip_address if device else 'device'}: "
                f"{test.probes_received}/{test.probes_sent} replies, {loss_text}.",
                "timestamp": test.completed_at or test.started_at,
                "status": test.status,
            }
        )
    for session in db.scalars(
        select(MonitoringSession).order_by(MonitoringSession.started_at.desc()).limit(5)
    ).all():
        activity.append(
            {
                "activity_type": "monitoring",
                "title": "Monitoring session",
                "description": f"Interval {session.interval_seconds}s; {len(session.device_links)} device(s).",
                "timestamp": session.started_at,
                "status": session.status,
            }
        )
    for scan in db.scalars(select(SecurityScan).order_by(SecurityScan.started_at.desc()).limit(5)).all():
        device = db.get(Device, scan.device_id)
        activity.append(
            {
                "activity_type": "security",
                "title": "TCP service assessment",
                "description": f"{device.ip_address if device else 'device'} · profile {scan.profile_name}.",
                "timestamp": scan.completed_at or scan.started_at,
                "status": scan.status,
            }
        )
    for report in db.scalars(select(Report).order_by(Report.generated_at.desc()).limit(5)).all():
        activity.append(
            {
                "activity_type": "report",
                "title": "Report generated",
                "description": f"{report.report_type.upper()} report {report.file_name or ''}".strip(),
                "timestamp": report.generated_at,
                "status": report.status,
            }
        )

    activity.sort(key=lambda item: item["timestamp"], reverse=True)
    health = analytics["health_score"]
    health_label = "Insufficient data"
    if health:
        if health["score"] >= 85:
            health_label = "Good"
        elif health["score"] >= 65:
            health_label = "Fair"
        else:
            health_label = "Needs attention"

    warnings: list[str] = []
    if not devices:
        warnings.append("No devices recorded yet. Run a discovery scan to build the inventory.")
    if analytics["sample_count"] == 0:
        warnings.append("No connectivity measurements exist in the last 24 hours.")
    elif analytics["availability_percent"] is None:
        warnings.append("Availability and the health score require monitoring observations.")

    return {
        "devices_total": len(devices),
        "responding_hosts": responding,
        "no_icmp_hosts": no_icmp,
        "not_tested_hosts": not_tested,
        "avg_latency_ms": analytics["avg_latency_ms"],
        "packet_loss_percent": analytics["packet_loss_percent"],
        "health_score": health,
        "health_label": health_label,
        "last_scan_at": last_scan,
        "latest_observation_at": max(latest_times) if latest_times else None,
        "active_monitoring_sessions": int(active_sessions),
        "open_security_findings": int(open_findings),
        "reports_count": int(reports_count),
        "recent_activity": activity[:8],
        "warnings": warnings,
    }
