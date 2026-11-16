"""Deterministic, rule-based diagnostics.

Every recommendation is derived from a recorded observation and includes the
triggering condition.  Rules never claim a definitive root cause.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.models import (
    Device,
    MonitoringObservation,
    PingTest,
    SecurityFinding,
    SecurityScan,
)
from app.services.errors import NetPulseError

_SEVERITY_ORDER = {"warning": 0, "review": 1, "info": 2}


def _latest_ping_test(db: Session, device_id: int) -> PingTest | None:
    return db.scalars(
        select(PingTest)
        .where(PingTest.device_id == device_id, PingTest.status == "completed")
        .order_by(PingTest.completed_at.desc())
        .limit(1)
    ).first()


def _recent_observations(db: Session, device_id: int, limit: int = 20) -> list[MonitoringObservation]:
    return list(
        db.scalars(
            select(MonitoringObservation)
            .where(MonitoringObservation.device_id == device_id)
            .order_by(MonitoringObservation.observed_at.desc())
            .limit(limit)
        ).all()
    )


def _latest_security_scan(db: Session, device_id: int) -> SecurityScan | None:
    return db.scalars(
        select(SecurityScan)
        .where(SecurityScan.device_id == device_id, SecurityScan.status == "completed")
        .order_by(SecurityScan.started_at.desc())
        .limit(1)
    ).first()


def _recommendation(
    rule_id: str,
    title: str,
    severity: str,
    observed_condition: str,
    recommendation: str,
    created_at,
    device: Device | None = None,
    evidence: dict | None = None,
) -> dict:
    return {
        "rule_id": rule_id,
        "title": title,
        "severity": severity,
        "observed_condition": observed_condition,
        "recommendation": recommendation,
        "created_at": created_at,
        "device_id": device.id if device else None,
        "device_ip": device.ip_address if device else None,
        "evidence": evidence,
    }


def _device_recommendations(db: Session, device: Device) -> list[dict]:
    items: list[dict] = []
    observations = _recent_observations(db, device.id)
    latest_ping = _latest_ping_test(db, device.id)

    # Repeated no-ICMP-response observations.
    if observations:
        consecutive_failures = 0
        for observation in observations:
            if observation.icmp_success:
                break
            consecutive_failures += 1
        if consecutive_failures >= settings.icmp_failure_threshold:
            latest = observations[0]
            items.append(
                _recommendation(
                    "DIAG-REPEATED-ICMP-FAILURE",
                    "Repeated no-ICMP-response observations",
                    "warning",
                    (
                        f"{consecutive_failures} consecutive monitoring observations recorded no ICMP "
                        f"response for {device.ip_address} (latest {latest.observed_at.isoformat()}Z)."
                    ),
                    (
                        "Verify that the device is powered and addressed correctly, that ICMP is not "
                        "blocked by a firewall, and that the network path is intact. A missing ICMP reply "
                        "does not prove the device is offline."
                    ),
                    latest.observed_at,
                    device,
                    {"consecutive_failures": consecutive_failures, "threshold": settings.icmp_failure_threshold},
                )
            )

    # Intermittent state changes.
    if len(observations) >= 2:
        chronological = list(reversed(observations))
        transitions = sum(
            1
            for index in range(1, len(chronological))
            if chronological[index].icmp_success != chronological[index - 1].icmp_success
        )
        if transitions >= settings.state_change_threshold:
            latest = observations[0]
            items.append(
                _recommendation(
                    "DIAG-INTERMITTENT-CONNECTIVITY",
                    "Intermittent connectivity observations",
                    "warning",
                    (
                        f"{transitions} success/failure transitions were observed across the last "
                        f"{len(observations)} monitoring observations for {device.ip_address}."
                    ),
                    (
                        "Investigate intermittent signal quality, cabling, congestion, power saving "
                        "settings and intermediate network equipment. Compare several monitoring windows "
                        "before concluding a cause."
                    ),
                    latest.observed_at,
                    device,
                    {"transitions": transitions, "sample_size": len(observations)},
                )
            )

    # Packet loss from the latest completed ping batch.
    if latest_ping and latest_ping.packet_loss_percent is not None:
        if latest_ping.packet_loss_percent >= settings.packet_loss_warning_percent:
            items.append(
                _recommendation(
                    "DIAG-HIGH-PACKET-LOSS",
                    "Elevated packet loss on the latest ping test",
                    "warning",
                    (
                        f"The latest ping test for {device.ip_address} recorded "
                        f"{latest_ping.packet_loss_percent:g}% packet loss "
                        f"({latest_ping.probes_received}/{latest_ping.probes_sent} replies, "
                        f"threshold {settings.packet_loss_warning_percent:g}%)."
                    ),
                    (
                        "Inspect wireless signal strength, cabling, link utilisation and network "
                        "equipment. Repeat the test during a quiet period to determine whether loss is "
                        "persistent or intermittent."
                    ),
                    latest_ping.completed_at or latest_ping.started_at,
                    device,
                    {
                        "packet_loss_percent": latest_ping.packet_loss_percent,
                        "probes_sent": latest_ping.probes_sent,
                        "probes_received": latest_ping.probes_received,
                        "test_id": latest_ping.id,
                    },
                )
            )

    # High latency from the latest completed ping batch.
    if latest_ping and latest_ping.avg_latency_ms is not None:
        if latest_ping.avg_latency_ms >= settings.high_latency_warning_ms:
            items.append(
                _recommendation(
                    "DIAG-HIGH-LATENCY",
                    "Average latency above the configured threshold",
                    "review",
                    (
                        f"The latest ping test for {device.ip_address} averaged "
                        f"{latest_ping.avg_latency_ms:g} ms (threshold "
                        f"{settings.high_latency_warning_ms:g} ms)."
                    ),
                    (
                        "Investigate congestion, wireless conditions and path quality. Use monitoring "
                        "history to check whether the latency is sustained or a single spike."
                    ),
                    latest_ping.completed_at or latest_ping.started_at,
                    device,
                    {
                        "avg_latency_ms": latest_ping.avg_latency_ms,
                        "min_latency_ms": latest_ping.min_latency_ms,
                        "max_latency_ms": latest_ping.max_latency_ms,
                        "test_id": latest_ping.id,
                    },
                )
            )

    # Port exposure findings from the most recent completed assessment.
    latest_scan = _latest_security_scan(db, device.id)
    if latest_scan:
        open_findings = [finding for finding in latest_scan.findings if finding.state == "open"]
        for finding in open_findings:
            if finding.port == 23:
                items.append(
                    _recommendation(
                        "DIAG-TELNET-OPEN",
                        "Telnet service accepting connections",
                        "review",
                        (
                            f"TCP port 23 (Telnet) accepted a connection on {device.ip_address} during "
                            f"the assessment at {latest_scan.started_at.isoformat()}Z."
                        ),
                        (
                            "Review whether Telnet is required. If not, disable it and use an encrypted "
                            "alternative such as SSH. This is an exposure observation, not proof of a "
                            "vulnerability."
                        ),
                        latest_scan.completed_at or latest_scan.started_at,
                        device,
                        {"port": 23, "scan_id": latest_scan.id, "state": finding.state},
                    )
                )
            elif finding.port == 21:
                items.append(
                    _recommendation(
                        "DIAG-FTP-OPEN",
                        "FTP service accepting connections",
                        "review",
                        (
                            f"TCP port 21 (FTP) accepted a connection on {device.ip_address} during the "
                            f"assessment at {latest_scan.started_at.isoformat()}Z."
                        ),
                        (
                            "Review whether FTP is required. Prefer an encrypted file transfer service. "
                            "This is an exposure observation, not proof of a vulnerability."
                        ),
                        latest_scan.completed_at or latest_scan.started_at,
                        device,
                        {"port": 21, "scan_id": latest_scan.id, "state": finding.state},
                    )
                )
            elif finding.port in (22, 3389):
                label = "SSH" if finding.port == 22 else "RDP"
                items.append(
                    _recommendation(
                        "DIAG-REMOTE-ADMIN-OPEN",
                        f"{label} remote administration accepting connections",
                        "review",
                        (
                            f"TCP port {finding.port} ({label}) accepted a connection on "
                            f"{device.ip_address} during the assessment at "
                            f"{latest_scan.started_at.isoformat()}Z."
                        ),
                        (
                            "Confirm that remote administration is required and restrict access to "
                            "trusted hosts and networks. This is an exposure observation, not proof of "
                            "a vulnerability."
                        ),
                        latest_scan.completed_at or latest_scan.started_at,
                        device,
                        {"port": finding.port, "scan_id": latest_scan.id, "state": finding.state},
                    )
                )
    return items


def build_recommendations(db: Session, device_id: int | None = None) -> list[dict]:
    if device_id is not None:
        device = db.get(Device, device_id)
        if device is None:
            raise NetPulseError(
                "DEVICE_NOT_FOUND", f"Device {device_id} was not found.", status_code=404
            )
        devices = [device]
    else:
        devices = list(db.scalars(select(Device).order_by(Device.ip_address)).all())

    items: list[dict] = []
    for device in devices:
        items.extend(_device_recommendations(db, device))

    if not items:
        has_data = db.scalar(select(func.count(PingTest.id))) or db.scalar(
            select(func.count(MonitoringObservation.id))
        )
        items.append(
            _recommendation(
                "DIAG-NO-DATA",
                "No evidence-based recommendations yet",
                "info",
                (
                    "No rule-triggering measurements have been recorded."
                    if has_data
                    else "No ping tests or monitoring observations have been recorded."
                ),
                (
                    "Run a discovery scan, ping a device and start monitoring. Recommendations "
                    "appear only when recorded observations match a documented rule."
                ),
                utcnow(),
                None,
                {"devices_evaluated": len(devices)},
            )
        )

    items.sort(
        key=lambda item: (
            _SEVERITY_ORDER.get(item["severity"], 3),
            -(item["created_at"].timestamp() if item["created_at"] else 0),
        )
    )
    return items
