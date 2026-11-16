"""Local network interface information.

Only values the operating system actually reports are returned.  Anything that
cannot be detected is ``None`` and accompanied by a warning rather than being
fabricated.
"""

from __future__ import annotations

import ipaddress
import logging
import platform
import re
import socket
import subprocess
from dataclasses import dataclass

import psutil

logger = logging.getLogger(__name__)

# Interface names that are usually virtual and should not be the primary target.
_VIRTUAL_HINTS = (
    "vpn",
    "tailscale",
    "zerotier",
    "wireguard",
    "loopback",
    "vmware",
    "virtualbox",
    "hyper-v",
    "docker",
    "vethernet",
    "bluetooth",
    "teredo",
    "isatap",
    "npcap",
)


@dataclass
class InterfaceInfo:
    interface_name: str | None
    local_ipv4: str | None
    subnet_mask: str | None
    network_cidr: str | None
    is_up: bool | None = None

    def as_dict(self) -> dict:
        return {
            "interface_name": self.interface_name,
            "local_ipv4": self.local_ipv4,
            "subnet_mask": self.subnet_mask,
            "network_cidr": self.network_cidr,
            "is_up": self.is_up,
        }


def network_cidr_for(ip_address: str, netmask: str) -> str | None:
    """Return the calculated network CIDR for an IPv4 address and netmask."""
    try:
        interface = ipaddress.IPv4Interface(f"{ip_address}/{netmask}")
    except ValueError:
        return None
    return str(interface.network)


def _is_usable_ipv4(address: str) -> bool:
    try:
        ip = ipaddress.IPv4Address(address)
    except ValueError:
        return False
    return not (ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified)


def detect_default_gateway() -> str | None:
    """Best-effort default gateway detection for Windows and Linux."""
    system = platform.system().lower()
    try:
        if system == "windows":
            completed = subprocess.run(
                ["route", "print", "-4"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            for line in completed.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    candidate = parts[2]
                    try:
                        ipaddress.IPv4Address(candidate)
                        return candidate
                    except ValueError:
                        continue
        else:
            completed = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            match = re.search(r"default\s+via\s+(\d+\.\d+\.\d+\.\d+)", completed.stdout)
            if match:
                return match.group(1)
    except (OSError, subprocess.SubprocessError):
        logger.debug("Default gateway detection failed", exc_info=True)
    return None


def _interface_score(name: str, is_up: bool, has_gateway: bool) -> tuple:
    lowered = name.lower()
    virtual = any(hint in lowered for hint in _VIRTUAL_HINTS)
    preferred_name = any(token in lowered for token in ("wi-fi", "wifi", "wlan", "ethernet", "eth"))
    return (
        0 if is_up else 1,
        0 if not virtual else 1,
        0 if has_gateway else 1,
        0 if preferred_name else 1,
        lowered,
    )


def get_network_info() -> dict:
    """Detect active interfaces and choose a primary local IPv4 interface."""
    warnings: list[str] = []
    gateway = detect_default_gateway()
    if gateway is None:
        warnings.append("Default gateway could not be detected on this platform.")

    stats = {}
    try:
        stats = psutil.net_if_stats()
    except Exception:
        logger.debug("Could not read interface statistics", exc_info=True)

    candidates: list[InterfaceInfo] = []
    try:
        addresses = psutil.net_if_addrs()
    except Exception as exc:  # pragma: no cover - platform failure
        logger.warning("Could not enumerate interfaces: %s", exc)
        return {
            "interface_name": None,
            "local_ipv4": None,
            "subnet_mask": None,
            "network_cidr": None,
            "default_gateway": gateway,
            "warnings": warnings + ["Network interfaces could not be enumerated."],
            "candidates": [],
        }

    for name, entries in addresses.items():
        nic_stats = stats.get(name)
        is_up = bool(nic_stats.isup) if nic_stats is not None else None
        for entry in entries:
            if entry.family != socket.AF_INET:
                continue
            if not _is_usable_ipv4(entry.address):
                continue
            netmask = entry.netmask or "255.255.255.255"
            cidr = network_cidr_for(entry.address, netmask)
            if cidr is None:
                continue
            candidates.append(
                InterfaceInfo(
                    interface_name=name,
                    local_ipv4=entry.address,
                    subnet_mask=netmask,
                    network_cidr=cidr,
                    is_up=is_up,
                )
            )

    if not candidates:
        warnings.append("No active non-loopback IPv4 interface was detected.")
        return {
            "interface_name": None,
            "local_ipv4": None,
            "subnet_mask": None,
            "network_cidr": None,
            "default_gateway": gateway,
            "warnings": warnings,
            "candidates": [],
        }

    def sort_key(candidate: InterfaceInfo) -> tuple:
        contains_gateway = False
        if gateway and candidate.network_cidr:
            try:
                contains_gateway = ipaddress.IPv4Address(gateway) in ipaddress.IPv4Network(
                    candidate.network_cidr, strict=False
                )
            except ValueError:
                contains_gateway = False
        return _interface_score(
            candidate.interface_name or "", bool(candidate.is_up), contains_gateway
        )

    candidates.sort(key=sort_key)
    primary = candidates[0]
    if len(candidates) > 1:
        warnings.append(
            f"{len(candidates)} active IPv4 interfaces were detected; "
            f"'{primary.interface_name}' was selected as the primary interface."
        )
    if gateway is None and primary.network_cidr:
        warnings.append(
            "Gateway is unavailable, so gateway-related topology and checks are omitted."
        )

    return {
        "interface_name": primary.interface_name,
        "local_ipv4": primary.local_ipv4,
        "subnet_mask": primary.subnet_mask,
        "network_cidr": primary.network_cidr,
        "default_gateway": gateway,
        "warnings": warnings,
        "candidates": [candidate.as_dict() for candidate in candidates],
    }
