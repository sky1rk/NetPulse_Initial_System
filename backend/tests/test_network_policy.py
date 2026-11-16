"""Network range validation, subnet arithmetic and discovery parsing."""

from __future__ import annotations

import ipaddress

import pytest

from app.services.discovery_service import (
    normalize_mac,
    parse_arp_table,
    usable_hosts,
    validate_scan_range,
)
from app.services.errors import NetPulseError
from app.services.network_info_service import network_cidr_for


def test_network_cidr_calculation():
    assert network_cidr_for("192.168.1.35", "255.255.255.0") == "192.168.1.0/24"
    assert network_cidr_for("10.20.30.40", "255.255.0.0") == "10.20.0.0/16"


def test_usable_hosts_excludes_network_and_broadcast():
    hosts = usable_hosts(ipaddress.ip_network("192.168.1.0/24"))
    assert len(hosts) == 254
    assert str(hosts[0]) == "192.168.1.1"
    assert str(hosts[-1]) == "192.168.1.254"


def test_scan_range_accepts_detected_subnet():
    network = validate_scan_range("192.168.1.0/24", "192.168.1.0/24", True, max_hosts=256)
    assert str(network) == "192.168.1.0/24"


def test_scan_range_requires_confirmation():
    with pytest.raises(NetPulseError) as error:
        validate_scan_range("192.168.1.0/24", "192.168.1.0/24", False)
    assert error.value.code == "AUTHORIZATION_REQUIRED"


def test_invalid_cidr_rejected():
    with pytest.raises(NetPulseError) as error:
        validate_scan_range("not-a-cidr", "192.168.1.0/24", True)
    assert error.value.code == "INVALID_SCAN_RANGE"


def test_public_range_rejected():
    with pytest.raises(NetPulseError) as error:
        validate_scan_range("8.8.8.0/24", "192.168.1.0/24", True, allow_custom=True)
    assert error.value.code == "PUBLIC_RANGE_NOT_ALLOWED"


def test_outside_local_subnet_rejected():
    with pytest.raises(NetPulseError) as error:
        validate_scan_range("10.0.0.0/24", "192.168.1.0/24", True)
    assert error.value.code == "OUTSIDE_LOCAL_SUBNET"


def test_host_count_limit_enforced():
    with pytest.raises(NetPulseError) as error:
        validate_scan_range("192.168.0.0/16", "192.168.0.0/16", True, max_hosts=256)
    assert error.value.code == "SCAN_RANGE_TOO_LARGE"


def test_arp_parsing_windows_style():
    output = """
Interface: 192.168.1.35 --- 0x8
  Internet Address      Physical Address      Type
  192.168.1.1           a4-2b-8c-11-22-33     dynamic
  192.168.1.1           ff-ff-ff-ff-ff-ff     static
  192.168.1.20          00-11-22-33-44-55     dynamic
"""
    entries = parse_arp_table(output)
    assert entries["192.168.1.1"] == "a4:2b:8c:11:22:33"
    assert entries["192.168.1.20"] == "00:11:22:33:44:55"


def test_arp_parsing_linux_style():
    output = "192.168.1.1 dev wlan0 lladdr AA:BB:CC:DD:EE:FF REACHABLE"
    assert parse_arp_table(output)["192.168.1.1"] == "aa:bb:cc:dd:ee:ff"


def test_normalize_mac_rejects_broadcast():
    assert normalize_mac("AA-BB-CC-DD-EE-FF") == "aa:bb:cc:dd:ee:ff"
    assert normalize_mac("ff:ff:ff:ff:ff:ff") is None
