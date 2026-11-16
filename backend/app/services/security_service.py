"""Limited TCP service exposure checks.

Only a configured allowlist of common ports is accepted.  Checks are simple TCP
connection attempts with short timeouts and bounded concurrency.  NetPulse does
not perform exploitation, credential testing, stealth or evasion.
"""

from __future__ import annotations

import errno
import logging
import socket
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.models import Device, SecurityFinding, SecurityScan
from app.services.devices_service import get_device_or_404
from app.services.errors import NetPulseError

logger = logging.getLogger(__name__)

PORT_SERVICES: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    3306: "MySQL",
    3389: "RDP",
    8080: "HTTP alternate",
}

PORT_PROFILES: dict[str, dict] = {
    "common_services": {
        "description": "Common local service ports used for a basic exposure review.",
        "ports": [21, 22, 23, 80, 443, 3389],
    },
    "web_services": {
        "description": "Common web service ports.",
        "ports": [80, 443, 8080],
    },
    "remote_administration": {
        "description": "Common remote administration ports requiring restricted access.",
        "ports": [22, 23, 3389],
    },
}

OPEN_STATES = {"open"}


def service_name(port: int) -> str | None:
    return PORT_SERVICES.get(port)


def _recommendation(port: int, state: str) -> tuple[str, str | None]:
    """Return (severity, recommendation) for an observed port state."""
    if state != "open":
        return "info", None
    if port == 23:
        return (
            "review",
            "Telnet is an insecure legacy service. If it is not required, disable it and use "
            "a secure alternative such as SSH. Restrict access if it must remain enabled.",
        )
    if port == 21:
        return (
            "review",
            "FTP sends credentials and data without encryption. Review whether it is required "
            "and prefer a secure file transfer service.",
        )
    if port in (22, 3389):
        return (
            "review",
            "Remote administration is exposed. Confirm that this access is required and restrict "
            "it to trusted hosts and networks.",
        )
    if port == 445:
        return (
            "review",
            "SMB file sharing is exposed. Confirm that sharing is required and restrict it to "
            "trusted networks.",
        )
    if port in (80, 443, 8080):
        return (
            "info",
            "A web service is accepting connections on this port. Confirm that the expected "
            "application is running and that it is kept up to date.",
        )
    return (
        "info",
        "A TCP service is accepting connections on this conventional port. Confirm that the "
        "service is expected and appropriately restricted.",
    )


def check_tcp_port(ip_address: str, port: int, timeout_seconds: float) -> str:
    """Attempt one TCP connection and classify the observed state."""
    try:
        with socket.create_connection((ip_address, port), timeout=timeout_seconds):
            return "open"
    except ConnectionRefusedError:
        return "closed_or_refused"
    except (TimeoutError, socket.timeout):
        return "filtered_or_timeout"
    except OSError as exc:
        if exc.errno in (errno.ECONNREFUSED, 10061):
            return "closed_or_refused"
        if exc.errno in (errno.ETIMEDOUT, 10060):
            return "filtered_or_timeout"
        logger.warning("TCP check error for %s:%s: %s", ip_address, port, exc)
        return "error"
    except Exception:  # pragma: no cover - defensive
        logger.exception("Unexpected TCP check failure for %s:%s", ip_address, port)
        return "error"


def validate_ports(requested: list[int] | None, profile_name: str | None) -> tuple[list[int], str]:
    allowlist = set(settings.allowed_port_list)
    profile = (profile_name or "common_services").strip()
    if requested is not None:
        ports = list(dict.fromkeys(requested))
        label = profile if profile in PORT_PROFILES else "custom_selection"
    elif profile in PORT_PROFILES:
        ports = list(PORT_PROFILES[profile]["ports"])
        label = profile
    else:
        raise NetPulseError(
            "UNKNOWN_PORT_PROFILE",
            f"Unknown port profile '{profile}'. Available profiles: {', '.join(PORT_PROFILES)}.",
            status_code=422,
        )

    if not ports:
        raise NetPulseError("INVALID_PORT_SELECTION", "At least one port must be selected.")
    if len(ports) > min(32, len(allowlist)):
        raise NetPulseError(
            "INVALID_PORT_SELECTION", "Too many ports were selected for one assessment.", status_code=422
        )
    disallowed = [port for port in ports if port not in allowlist]
    if disallowed:
        raise NetPulseError(
            "PORT_NOT_ALLOWED",
            (
                "The following ports are not in the configured allowlist: "
                f"{', '.join(str(port) for port in disallowed)}."
            ),
            status_code=422,
        )
    invalid = [port for port in ports if port < 1 or port > 65535]
    if invalid:
        raise NetPulseError("INVALID_PORT_SELECTION", "Ports must be between 1 and 65535.")
    return ports, label


def run_security_scan(
    db: Session,
    device_id: int,
    requested_ports: list[int] | None,
    profile_name: str | None,
    confirm_authorized: bool,
) -> tuple[SecurityScan, list[SecurityFinding], list[str]]:
    if not confirm_authorized:
        raise NetPulseError(
            "AUTHORIZATION_REQUIRED",
            "You must confirm that you are authorized to assess this device before a TCP check.",
            status_code=403,
        )
    device = get_device_or_404(db, device_id)
    ports, label = validate_ports(requested_ports, profile_name)

    scan = SecurityScan(
        device_id=device.id,
        started_at=utcnow(),
        profile_name=label,
        status="running",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    warnings: list[str] = []
    findings: list[SecurityFinding] = []
    timeout_seconds = max(0.05, settings.security_timeout_ms / 1000)

    try:
        with ThreadPoolExecutor(max_workers=max(1, settings.security_max_concurrency)) as executor:
            states = list(
                executor.map(
                    lambda port: check_tcp_port(device.ip_address, port, timeout_seconds), ports
                )
            )
        for port, state in zip(ports, states):
            severity, recommendation = _recommendation(port, state)
            finding = SecurityFinding(
                security_scan_id=scan.id,
                port=port,
                protocol="tcp",
                state=state,
                service_name=service_name(port),
                severity=severity,
                recommendation=recommendation,
            )
            db.add(finding)
            findings.append(finding)
        scan.completed_at = utcnow()
        scan.status = "completed"
        if not any(finding.state == "open" for finding in findings):
            warnings.append(
                "No open ports were observed in the tested profile. This does not mean the "
                "device is secure; only the selected ports were checked."
            )
        db.commit()
        for finding in findings:
            db.refresh(finding)
        db.refresh(scan)
        return scan, findings, warnings
    except NetPulseError:
        raise
    except Exception as exc:
        logger.exception("Security scan failed for device %s", device_id)
        scan.status = "failed"
        scan.completed_at = utcnow()
        scan.error_message = "The assessment failed unexpectedly."
        db.commit()
        raise NetPulseError(
            "SECURITY_SCAN_FAILED",
            "The TCP service assessment failed unexpectedly. Review the backend log.",
            status_code=500,
        ) from exc


def list_findings(
    db: Session,
    device_id: int | None = None,
    state: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[dict]]:
    query = (
        select(SecurityFinding, SecurityScan, Device)
        .join(SecurityScan, SecurityFinding.security_scan_id == SecurityScan.id)
        .join(Device, SecurityScan.device_id == Device.id)
        .order_by(SecurityScan.started_at.desc(), SecurityFinding.port.asc())
    )
    if device_id is not None:
        query = query.where(SecurityScan.device_id == device_id)
    if state:
        query = query.where(SecurityFinding.state == state)

    rows = db.execute(query).all()
    records: list[dict] = []
    for finding, scan, device in rows:
        records.append(
            {
                "id": finding.id,
                "scan_id": scan.id,
                "device_id": device.id,
                "device_ip": device.ip_address,
                "scanned_at": scan.started_at,
                "scan_status": scan.status,
                "port": finding.port,
                "protocol": finding.protocol,
                "state": finding.state,
                "service_name": finding.service_name,
                "severity": finding.severity,
                "recommendation": finding.recommendation,
            }
        )
    total = len(records)
    return total, records[offset : offset + limit]


def scan_summaries(db: Session, device_id: int | None = None, limit: int = 50) -> list[dict]:
    query = select(SecurityScan, Device).join(Device, SecurityScan.device_id == Device.id)
    if device_id is not None:
        query = query.where(SecurityScan.device_id == device_id)
    query = query.order_by(SecurityScan.started_at.desc()).limit(limit)
    summaries: list[dict] = []
    for scan, device in db.execute(query).all():
        open_count = len([finding for finding in scan.findings if finding.state == "open"])
        summaries.append(
            {
                "scan_id": scan.id,
                "device_id": device.id,
                "device_ip": device.ip_address,
                "status": scan.status,
                "profile_name": scan.profile_name,
                "started_at": scan.started_at,
                "completed_at": scan.completed_at,
                "open_port_count": open_count,
                "tested_port_count": len(scan.findings),
            }
        )
    return summaries
