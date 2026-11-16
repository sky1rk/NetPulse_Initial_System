"""Device inventory queries and latest-observation derivation."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import (
    Device,
    MonitoringObservation,
    NetworkScan,
    NetworkScanDevice,
    PingTest,
    SecurityScan,
)
from app.services.errors import NetPulseError


def _latest_ping_tests(db: Session, device_ids: list[int] | None = None) -> dict[int, PingTest]:
    latest = (
        select(PingTest.device_id, func.max(PingTest.completed_at).label("observed_at"))
        .where(PingTest.status == "completed", PingTest.completed_at.is_not(None))
        .group_by(PingTest.device_id)
        .subquery()
    )
    query = select(PingTest).join(
        latest,
        and_(PingTest.device_id == latest.c.device_id, PingTest.completed_at == latest.c.observed_at),
    )
    if device_ids:
        query = query.where(PingTest.device_id.in_(device_ids))
    return {test.device_id: test for test in db.scalars(query).all()}


def _latest_monitoring_observations(
    db: Session, device_ids: list[int] | None = None
) -> dict[int, MonitoringObservation]:
    latest = (
        select(
            MonitoringObservation.device_id,
            func.max(MonitoringObservation.observed_at).label("observed_at"),
        )
        .group_by(MonitoringObservation.device_id)
        .subquery()
    )
    query = select(MonitoringObservation).join(
        latest,
        and_(
            MonitoringObservation.device_id == latest.c.device_id,
            MonitoringObservation.observed_at == latest.c.observed_at,
        ),
    )
    if device_ids:
        query = query.where(MonitoringObservation.device_id.in_(device_ids))
    return {observation.device_id: observation for observation in db.scalars(query).all()}


def _latest_scan_links(db: Session, device_ids: list[int] | None = None) -> dict[int, NetworkScanDevice]:
    query = (
        select(NetworkScanDevice)
        .join(NetworkScan, NetworkScanDevice.scan_id == NetworkScan.id)
        .where(NetworkScan.status.in_(["completed", "partial"]))
        .order_by(NetworkScan.started_at.asc())
    )
    if device_ids:
        query = query.where(NetworkScanDevice.device_id.in_(device_ids))
    links: dict[int, NetworkScanDevice] = {}
    for link in db.scalars(query).all():
        links[link.device_id] = link
    return links


def latest_observations(db: Session, device_ids: list[int] | None = None) -> dict[int, dict]:
    """Combine the most recent ping, monitoring and scan observation per device."""
    pings = _latest_ping_tests(db, device_ids)
    monitoring = _latest_monitoring_observations(db, device_ids)
    scans = _latest_scan_links(db, device_ids)

    candidates: dict[int, list[tuple]] = {}
    for device_id, test in pings.items():
        observation = "responding" if test.probes_received > 0 else "no_icmp_response"
        candidates.setdefault(device_id, []).append(
            (
                test.completed_at or test.started_at,
                {
                    "latest_observation": observation,
                    "latest_latency_ms": test.avg_latency_ms,
                    "latest_observation_at": test.completed_at or test.started_at,
                    "latest_packet_loss_percent": test.packet_loss_percent,
                    "source": "ping",
                    "ping_test_id": test.id,
                },
            )
        )
    for device_id, observation in monitoring.items():
        candidates.setdefault(device_id, []).append(
            (
                observation.observed_at,
                {
                    "latest_observation": observation.observation,
                    "latest_latency_ms": observation.latency_ms,
                    "latest_observation_at": observation.observed_at,
                    "latest_packet_loss_percent": None,
                    "source": "monitoring",
                    "monitoring_observation_id": observation.id,
                },
            )
        )
    for device_id, link in scans.items():
        scan = db.get(NetworkScan, link.scan_id)
        observed_at = scan.completed_at or scan.started_at if scan else None
        candidates.setdefault(device_id, []).append(
            (
                observed_at,
                {
                    "latest_observation": link.observation,
                    "latest_latency_ms": None,
                    "latest_observation_at": observed_at,
                    "latest_packet_loss_percent": None,
                    "source": "scan",
                },
            )
        )

    result: dict[int, dict] = {}
    for device_id, entries in candidates.items():
        entries = [entry for entry in entries if entry[0] is not None]
        if not entries:
            continue
        entries.sort(key=lambda entry: entry[0])
        result[device_id] = entries[-1][1]
    return result


def observation_for_device(db: Session, device_id: int) -> dict:
    return latest_observations(db, [device_id]).get(
        device_id,
        {
            "latest_observation": "not_tested",
            "latest_latency_ms": None,
            "latest_observation_at": None,
            "latest_packet_loss_percent": None,
            "source": None,
        },
    )


def list_devices(
    db: Session,
    status: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[dict]]:
    """Return devices enriched with their latest observation."""
    devices = db.scalars(select(Device).order_by(Device.ip_address)).all()
    observations = latest_observations(db, [device.id for device in devices])

    items: list[dict] = []
    for device in devices:
        record = {
            "id": device.id,
            "ip_address": device.ip_address,
            "mac_address": device.mac_address,
            "hostname": device.hostname,
            "vendor": device.vendor,
            "first_seen": device.first_seen,
            "last_seen": device.last_seen,
            "created_at": device.created_at,
            "updated_at": device.updated_at,
            **observations.get(
                device.id,
                {
                    "latest_observation": "not_tested",
                    "latest_latency_ms": None,
                    "latest_observation_at": None,
                    "latest_packet_loss_percent": None,
                },
            ),
        }
        if status and record["latest_observation"] != status:
            continue
        if search:
            needle = search.strip().lower()
            haystack = " ".join(
                filter(
                    None,
                    [device.ip_address, device.hostname, device.mac_address, device.vendor],
                )
            ).lower()
            if needle not in haystack:
                continue
        items.append(record)

    total = len(items)
    return total, items[offset : offset + limit]


def get_device_or_404(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise NetPulseError("DEVICE_NOT_FOUND", f"Device {device_id} was not found.", status_code=404)
    return device


def get_device_detail(db: Session, device_id: int) -> dict:
    device = get_device_or_404(db, device_id)
    observation = observation_for_device(db, device_id)
    recent_pings = db.scalars(
        select(PingTest)
        .where(PingTest.device_id == device_id)
        .order_by(PingTest.started_at.desc())
        .limit(5)
    ).all()
    recent_observations = db.scalars(
        select(MonitoringObservation)
        .where(MonitoringObservation.device_id == device_id)
        .order_by(MonitoringObservation.observed_at.desc())
        .limit(10)
    ).all()
    recent_scans = db.scalars(
        select(SecurityScan)
        .where(SecurityScan.device_id == device_id)
        .order_by(SecurityScan.started_at.desc())
        .limit(5)
    ).all()
    return {
        "id": device.id,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "hostname": device.hostname,
        "vendor": device.vendor,
        "first_seen": device.first_seen,
        "last_seen": device.last_seen,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        **observation,
        "recent_ping_tests": recent_pings,
        "recent_observations": recent_observations,
        "recent_security_scans": recent_scans,
    }
