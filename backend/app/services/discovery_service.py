"""Bounded local-subnet discovery.

Discovery uses a ping sweep for responsiveness plus the operating system ARP /
neighbour table for best-effort MAC addresses.  It never scans public ranges,
never exceeds the configured host limit, and never invents a MAC address or
hostname that the OS did not report.
"""

from __future__ import annotations

import ipaddress
import logging
import platform
import re
import shutil
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import utcnow
from app.models import Device, NetworkScan, NetworkScanDevice
from app.services import network_info_service
from app.services.connectivity_service import PingUtilityUnavailable, ping_once
from app.services.errors import NetPulseError

logger = logging.getLogger(__name__)

_MAC_PATTERN = re.compile(r"\b([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})\b")
_IPV4_PATTERN = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")


@dataclass
class HostObservation:
    ip_address: str
    mac_address: str | None
    hostname: str | None
    observation: str


def usable_hosts(network: ipaddress.IPv4Network) -> list[ipaddress.IPv4Address]:
    """Return scannable host addresses, excluding network/broadcast addresses."""
    if network.prefixlen >= 31:
        return list(network)
    return [address for address in network.hosts()]


def validate_scan_range(
    requested_cidr: str | None,
    local_cidr: str | None,
    confirm_authorized: bool,
    max_hosts: int | None = None,
    allow_custom: bool | None = None,
) -> ipaddress.IPv4Network:
    """Validate the requested CIDR against authorization and safety policy."""
    max_hosts = settings.max_scan_hosts if max_hosts is None else max_hosts
    allow_custom = settings.allow_custom_scan_range if allow_custom is None else allow_custom

    if not confirm_authorized:
        raise NetPulseError(
            "AUTHORIZATION_REQUIRED",
            "You must confirm that you own or are authorized to assess this network.",
            status_code=403,
        )

    if not requested_cidr:
        if not local_cidr:
            raise NetPulseError(
                "LOCAL_NETWORK_UNAVAILABLE",
                "No local subnet could be detected; provide an authorized CIDR explicitly.",
                status_code=409,
            )
        requested_cidr = local_cidr

    try:
        network = ipaddress.ip_network(requested_cidr, strict=False)
    except ValueError as exc:
        raise NetPulseError(
            "INVALID_SCAN_RANGE", f"'{requested_cidr}' is not a valid CIDR range."
        ) from exc

    if network.version != 4:
        raise NetPulseError("INVALID_SCAN_RANGE", "Only IPv4 ranges are supported.")
    if not network.is_private:
        raise NetPulseError(
            "PUBLIC_RANGE_NOT_ALLOWED",
            "Discovery is restricted to private local networks. Public ranges are not scanned.",
            status_code=403,
        )

    host_count = len(usable_hosts(network))
    if host_count > max_hosts:
        raise NetPulseError(
            "SCAN_RANGE_TOO_LARGE",
            f"The range contains {host_count} hosts, above the configured maximum of {max_hosts}.",
            status_code=422,
        )
    if host_count == 0:
        raise NetPulseError("INVALID_SCAN_RANGE", "The range contains no scannable host addresses.")

    if local_cidr:
        try:
            local_network = ipaddress.ip_network(local_cidr, strict=False)
        except ValueError:
            local_network = None
        if local_network is not None:
            inside_local = network.subnet_of(local_network) or network == local_network
            if not inside_local and not allow_custom:
                raise NetPulseError(
                    "OUTSIDE_LOCAL_SUBNET",
                    (
                        "The requested range is outside the detected local subnet. "
                        "Only the detected local subnet may be scanned by default."
                    ),
                    status_code=403,
                )
    elif not allow_custom:
        raise NetPulseError(
            "LOCAL_NETWORK_UNAVAILABLE",
            "The local subnet could not be detected, so a scan cannot be authorised automatically.",
            status_code=409,
        )

    return network


def normalize_mac(value: str) -> str | None:
    """Normalise a MAC address and reject broadcast/multicast values."""
    cleaned = value.strip().replace("-", ":").lower()
    try:
        octets = [int(part, 16) for part in cleaned.split(":")]
    except ValueError:
        return None
    if len(octets) != 6 or any(octet < 0 or octet > 255 for octet in octets):
        return None
    # Reject multicast/broadcast (first octet least-significant bit set).
    if octets[0] & 1:
        return None
    return ":".join(f"{octet:02x}" for octet in octets)


def parse_arp_table(output: str) -> dict[str, str]:
    """Parse Windows ``arp -a`` or Linux ``arp``/``ip neigh`` output."""
    entries: dict[str, str] = {}
    for line in output.splitlines():
        ip_match = _IPV4_PATTERN.search(line)
        if not ip_match:
            continue
        ip_value = ip_match.group(1)
        try:
            ipaddress.IPv4Address(ip_value)
        except ValueError:
            continue
        mac_match = _MAC_PATTERN.search(line)
        if not mac_match:
            continue
        mac = normalize_mac(mac_match.group(1))
        if mac:
            entries[ip_value] = mac
    return entries


def read_arp_table() -> tuple[dict[str, str], str | None]:
    """Read the local ARP/neighbour table; return entries and an optional warning."""
    system = platform.system().lower()
    commands: list[list[str]]
    if system == "windows":
        commands = [["arp", "-a"]]
    else:
        commands = [["ip", "neigh", "show"], ["arp", "-an"]]
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if completed.returncode == 0 and completed.stdout.strip():
            return parse_arp_table(completed.stdout), None
    return {}, "The operating system ARP/neighbour table could not be read."


def lookup_hostname(ip_address: str) -> str | None:
    """Best-effort reverse lookup; failures return ``None``."""
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname or None
    except (OSError, socket.herror, socket.gaierror):
        return None


def discover_hosts(
    network: ipaddress.IPv4Network,
    timeout_ms: int | None = None,
    concurrency: int | None = None,
) -> tuple[list[HostObservation], list[str]]:
    """Perform a bounded ping sweep and combine it with the ARP table."""
    timeout_ms = timeout_ms or settings.scan_ping_timeout_ms
    concurrency = concurrency or settings.scan_concurrency
    warnings: list[str] = []
    addresses = [str(address) for address in usable_hosts(network)]
    responding: set[str] = set()

    if shutil.which("ping") is None:
        warnings.append(
            "The platform ping utility was not found, so readiness probing was skipped. "
            "Discovery is limited to the local ARP/neighbour table."
        )
    else:
        ping_errors = 0
        with ThreadPoolExecutor(max_workers=max(1, min(concurrency, 64))) as executor:
            futures = {
                executor.submit(ping_once, address, timeout_ms): address for address in addresses
            }
            for future in as_completed(futures):
                address = futures[future]
                try:
                    if future.result().success:
                        responding.add(address)
                except PingUtilityUnavailable as exc:
                    ping_errors += 1
                    if ping_errors == 1:
                        warnings.append(f"Ping probing was interrupted: {exc}")
                except Exception:  # pragma: no cover - defensive
                    logger.debug("Probe failed for %s", address, exc_info=True)
        if ping_errors:
            warnings.append(
                f"{ping_errors} probe(s) could not be executed; results may be partial."
            )

    arp_entries, arp_warning = read_arp_table()
    if arp_warning:
        warnings.append(arp_warning)

    observed_ips = set(responding)
    for ip_value, mac in arp_entries.items():
        if ip_value in addresses:
            observed_ips.add(ip_value)

    hostnames: dict[str, str | None] = {}
    if observed_ips:
        with ThreadPoolExecutor(max_workers=min(8, len(observed_ips))) as executor:
            futures = {executor.submit(lookup_hostname, ip): ip for ip in observed_ips}
            for future, ip in futures.items():
                try:
                    hostnames[ip] = future.result(timeout=2.0)
                except Exception:
                    hostnames[ip] = None

    observations: list[HostObservation] = []
    for ip_value in sorted(observed_ips, key=lambda value: ipaddress.IPv4Address(value)):
        observations.append(
            HostObservation(
                ip_address=ip_value,
                mac_address=arp_entries.get(ip_value),
                hostname=hostnames.get(ip_value),
                observation="responding" if ip_value in responding else "no_icmp_response",
            )
        )

    if not observations:
        warnings.append(
            "No hosts were observed. Client isolation, firewalls, ICMP filtering or missing "
            "permissions can limit discovery; unobserved addresses are not necessarily unused."
        )
    return observations, warnings


def persist_scan(
    db: Session,
    network_cidr: str,
    interface_name: str | None,
    observations: list[HostObservation],
    warnings: list[str],
    started_at,
) -> tuple[NetworkScan, list[tuple[NetworkScanDevice, Device]]]:
    """Upsert discovered devices and associate them with the scan session."""
    scan = NetworkScan(
        network_cidr=network_cidr,
        interface_name=interface_name,
        started_at=started_at,
        completed_at=utcnow(),
        status="completed",
        discovered_count=len(observations),
        warnings="\n".join(warnings) if warnings else None,
    )
    db.add(scan)
    db.flush()

    links: list[tuple[NetworkScanDevice, Device]] = []
    now = utcnow()
    for host in observations:
        device = db.scalar(select(Device).where(Device.ip_address == host.ip_address))
        if device is None:
            device = Device(
                ip_address=host.ip_address,
                mac_address=host.mac_address,
                hostname=host.hostname,
                first_seen=now,
                last_seen=now,
            )
            db.add(device)
            db.flush()
        else:
            if host.mac_address:
                device.mac_address = host.mac_address
            if host.hostname:
                device.hostname = host.hostname
            device.last_seen = now
        link = NetworkScanDevice(scan_id=scan.id, device_id=device.id, observation=host.observation)
        db.add(link)
        links.append((link, device))

    db.commit()
    db.refresh(scan)
    return scan, links


def run_scan(
    db: Session,
    requested_cidr: str | None,
    confirm_authorized: bool,
) -> tuple[NetworkScan, list[tuple[NetworkScanDevice, Device]], list[str]]:
    """Validate, execute and persist a discovery attempt."""
    info = network_info_service.get_network_info()
    warnings = list(info.get("warnings") or [])
    network = validate_scan_range(
        requested_cidr=requested_cidr,
        local_cidr=info.get("network_cidr"),
        confirm_authorized=confirm_authorized,
    )

    started_at = utcnow()
    try:
        observations, discovery_warnings = discover_hosts(network)
        warnings.extend(discovery_warnings)
        scan, links = persist_scan(
            db,
            network_cidr=str(network),
            interface_name=info.get("interface_name"),
            observations=observations,
            warnings=warnings,
            started_at=started_at,
        )
        return scan, links, warnings
    except NetPulseError:
        raise
    except Exception as exc:
        logger.exception("Discovery scan failed")
        failed = NetworkScan(
            network_cidr=str(network),
            interface_name=info.get("interface_name"),
            started_at=started_at,
            completed_at=utcnow(),
            status="failed",
            discovered_count=0,
            warnings="\n".join(warnings) if warnings else None,
        )
        db.add(failed)
        db.commit()
        raise NetPulseError(
            "SCAN_FAILED",
            "The discovery scan failed unexpectedly. Review the backend log for details.",
            status_code=500,
        ) from exc


def build_topology(db: Session, network_info: dict | None = None) -> dict:
    """Build a logical (not physical) topology of known devices."""
    from app.schemas.network import TopologyEdge, TopologyNode, TopologyResponse
    from app.services.devices_service import latest_observations

    info = network_info or network_info_service.get_network_info()
    warnings = list(info.get("warnings") or [])
    local_ip = info.get("local_ipv4")
    local_device = db.scalar(select(Device).where(Device.ip_address == local_ip)) if local_ip else None
    nodes = [
        TopologyNode(
            id="local-host",
            label=f"Monitoring host ({info.get('interface_name') or 'local'})",
            node_type="local_host",
            ip_address=local_ip,
            mac_address=local_device.mac_address if local_device else None,
        )
    ]
    edges: list[TopologyEdge] = []

    gateway = info.get("default_gateway")
    if gateway:
        gateway_node = TopologyNode(
            id=f"gateway-{gateway}",
            label="Default gateway",
            node_type="gateway",
            ip_address=gateway,
            inferred=False,
        )
        nodes.append(gateway_node)
        edges.append(
            TopologyEdge(source="local-host", target=gateway_node.id, label="default route", inferred=False)
        )
    else:
        warnings.append("Default gateway is unavailable; the gateway node is omitted.")

    latest = latest_observations(db)
    devices = db.scalars(select(Device).order_by(Device.ip_address)).all()
    for device in devices:
        if gateway and device.ip_address == gateway:
            continue
        if local_ip and device.ip_address == local_ip:
            # The monitoring host already has its own node.
            continue
        observation = latest.get(device.id, {})
        node = TopologyNode(
            id=f"device-{device.id}",
            label=device.hostname or device.ip_address,
            node_type="device",
            ip_address=device.ip_address,
            mac_address=device.mac_address,
            observation=observation.get("observation"),
            inferred=True,
        )
        nodes.append(node)
        edges.append(
            TopologyEdge(
                source=f"gateway-{gateway}" if gateway else "local-host",
                target=node.id,
                label="observed on local subnet",
                inferred=True,
            )
        )

    if not devices:
        warnings.append("No devices have been recorded yet; run a discovery scan to populate the topology.")

    response = TopologyResponse(nodes=nodes, edges=edges, local_host=nodes[0], warnings=warnings)
    return response.model_dump()
