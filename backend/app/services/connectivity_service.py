"""ICMP connectivity testing through the platform ping utility.

The utility is invoked with an argument list (never a shell string), a
subprocess timeout, and a bounded probe count.  A failed probe stores a null
latency; it is never recorded as zero.
"""

from __future__ import annotations

import logging
import math
import platform
import re
import subprocess
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.models import Device, PingProbe, PingTest
from app.services import metrics
from app.services.errors import NetPulseError

logger = logging.getLogger(__name__)

_LATENCY_PATTERN = re.compile(r"time[=<]\s*([\d.]+)\s*ms", re.IGNORECASE)
_TTL_PATTERN = re.compile(r"\bttl[=\s:]+(\d+)", re.IGNORECASE)


class PingUtilityUnavailable(RuntimeError):
    """Raised when the platform ping executable cannot be run."""


@dataclass
class ProbeResult:
    success: bool
    latency_ms: float | None = None
    error_message: str | None = None


def build_ping_command(ip_address: str, timeout_ms: int, count: int = 1) -> list[str]:
    """Build a platform-aware ping command as an argument list."""
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", str(count), "-w", str(timeout_ms), ip_address]
    if system == "darwin":
        return ["ping", "-c", str(count), "-W", str(timeout_ms), ip_address]
    # Linux iputils interprets -W in seconds.
    wait_seconds = max(1, math.ceil(timeout_ms / 1000))
    return ["ping", "-c", str(count), "-W", str(wait_seconds), ip_address]


def parse_latency_ms(output: str) -> float | None:
    """Extract the first reported round-trip time from ping output."""
    match = _LATENCY_PATTERN.search(output)
    if not match:
        return None
    try:
        return round(float(match.group(1)), 2)
    except ValueError:
        return None


def _subprocess_kwargs() -> dict:
    if platform.system().lower() == "windows":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def ping_once(ip_address: str, timeout_ms: int) -> ProbeResult:
    """Send one ICMP echo request and report the observed result."""
    command = build_ping_command(ip_address, timeout_ms, count=1)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(2.0, (timeout_ms / 1000) + 2.0),
            check=False,
            **_subprocess_kwargs(),
        )
    except FileNotFoundError as exc:
        raise PingUtilityUnavailable(
            "The platform ping utility was not found. Install iputils-ping or enable ping.exe."
        ) from exc
    except subprocess.TimeoutExpired:
        return ProbeResult(False, None, "Ping process exceeded its subprocess timeout.")
    except OSError as exc:
        logger.warning("Ping execution failed for %s: %s", ip_address, exc)
        return ProbeResult(False, None, "Ping could not be executed on this platform.")

    output = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    latency = parse_latency_ms(output)
    replied = bool(_TTL_PATTERN.search(output))
    success = completed.returncode == 0 and (replied or latency is not None)

    if success:
        if latency is None:
            latency = round((time.perf_counter() - started) * 1000, 2)
        return ProbeResult(True, latency, None)

    if completed.returncode != 0 and not output.strip():
        message = "No ICMP reply (utility returned a non-zero status)."
    elif re.search(r"could not find host|name or service not known|unknown host", output, re.I):
        message = "Host could not be resolved by the ping utility."
    elif re.search(r"destination (host|net) unreachable", output, re.I):
        message = "Destination unreachable (ICMP unreachable was reported)."
    else:
        message = "No ICMP reply within the configured timeout."
    return ProbeResult(False, None, message)


def execute_ping_test(
    db: Session,
    device: Device,
    count: int | None = None,
    timeout_ms: int | None = None,
) -> dict:
    """Run and persist a bounded ping batch for one device."""
    count = settings.ping_default_count if count is None else count
    timeout_ms = settings.ping_default_timeout_ms if timeout_ms is None else timeout_ms

    if count < 1:
        raise NetPulseError("INVALID_PROBE_COUNT", "Probe count must be at least 1.")
    if count > settings.ping_max_count:
        raise NetPulseError(
            "INVALID_PROBE_COUNT",
            f"Probe count must not exceed the configured maximum of {settings.ping_max_count}.",
            status_code=422,
        )
    if timeout_ms < settings.ping_min_timeout_ms or timeout_ms > settings.ping_max_timeout_ms:
        raise NetPulseError(
            "INVALID_TIMEOUT",
            (
                "Timeout must be between "
                f"{settings.ping_min_timeout_ms} and {settings.ping_max_timeout_ms} ms."
            ),
            status_code=422,
        )

    test = PingTest(device_id=device.id, started_at=utcnow(), probes_sent=0, probes_received=0, status="running")
    db.add(test)
    db.commit()
    db.refresh(test)

    samples: list[float] = []
    received = 0
    utility_error: str | None = None

    for sequence in range(1, count + 1):
        try:
            result = ping_once(device.ip_address, timeout_ms)
        except PingUtilityUnavailable as exc:
            utility_error = str(exc)
            break

        probe = PingProbe(
            ping_test_id=test.id,
            sequence_number=sequence,
            tested_at=utcnow(),
            success=result.success,
            latency_ms=result.latency_ms if result.success else None,
            error_message=None if result.success else result.error_message,
        )
        db.add(probe)
        if result.success and result.latency_ms is not None:
            samples.append(result.latency_ms)
            received += 1
        db.flush()

    sent = count if utility_error is None else max(0, len(test.probes))

    if utility_error is not None:
        test.status = "failed"
        test.error_message = utility_error
        test.completed_at = utcnow()
        test.probes_sent = sent
        test.probes_received = received
        test.packet_loss_percent = metrics.packet_loss_percent(sent, received)
        stats = metrics.latency_statistics(samples)
        for key, value in stats.items():
            setattr(test, key, value)
        db.commit()
        db.refresh(test)
        raise NetPulseError("PING_UTILITY_UNAVAILABLE", utility_error, status_code=503)

    stats = metrics.latency_statistics(samples)
    test.probes_sent = count
    test.probes_received = received
    test.packet_loss_percent = metrics.packet_loss_percent(count, received)
    test.avg_latency_ms = stats["avg_latency_ms"]
    test.min_latency_ms = stats["min_latency_ms"]
    test.max_latency_ms = stats["max_latency_ms"]
    test.completed_at = utcnow()
    test.status = "completed"
    db.commit()
    db.refresh(test)

    message = None
    if received == 0:
        message = (
            "No ICMP replies were received. This is an observation only; ICMP may be blocked "
            "and does not prove the device is offline."
        )
    return {
        "test": test,
        "jitter_ms": metrics.jitter_ms(samples),
        "message": message,
    }


def execute_single_probe(ip_address: str, timeout_ms: int | None = None) -> ProbeResult:
    """Convenience helper used by the monitoring loop."""
    return ping_once(ip_address, timeout_ms or settings.ping_default_timeout_ms)
