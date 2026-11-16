"""API contract tests for dashboard, discovery and devices."""

from __future__ import annotations

from app.models import Device
from app.services import connectivity_service, discovery_service
from app.services.connectivity_service import ProbeResult


def _network_info():
    return {
        "interface_name": "Wi-Fi",
        "local_ipv4": "192.168.1.35",
        "subnet_mask": "255.255.255.0",
        "network_cidr": "192.168.1.0/24",
        "default_gateway": "192.168.1.1",
        "warnings": [],
        "candidates": [],
    }


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["timestamp"].endswith("Z")


def test_empty_dashboard_is_honest(client):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["devices_total"] == 0
    assert payload["responding_hosts"] == 0
    assert payload["avg_latency_ms"] is None
    assert payload["packet_loss_percent"] is None
    assert payload["health_score"] is None
    assert payload["health_label"] == "Insufficient data"
    assert payload["warnings"]


def test_empty_device_list(client):
    response = client.get("/api/devices")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 100, "offset": 0}


def test_scan_requires_confirmation(client):
    response = client.post(
        "/api/network/scan", json={"network_cidr": "192.168.1.0/24", "confirm_authorized": False}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_REQUIRED"


def test_scan_rejects_outside_range(client, monkeypatch):
    monkeypatch.setattr(discovery_service.network_info_service, "get_network_info", _network_info)
    response = client.post(
        "/api/network/scan", json={"network_cidr": "10.0.0.0/24", "confirm_authorized": True}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "OUTSIDE_LOCAL_SUBNET"


def test_scan_persists_devices_and_handles_missing_fields(client, monkeypatch):
    monkeypatch.setattr(discovery_service.network_info_service, "get_network_info", _network_info)

    def fake_discover(network, timeout_ms=None, concurrency=None):
        return (
            [
                discovery_service.HostObservation(
                    ip_address="192.168.1.1",
                    mac_address="a4:2b:8c:11:22:33",
                    hostname="router.local",
                    observation="responding",
                ),
                discovery_service.HostObservation(
                    ip_address="192.168.1.20",
                    mac_address=None,
                    hostname=None,
                    observation="no_icmp_response",
                ),
            ],
            ["Partial observation warning"],
        )

    monkeypatch.setattr(discovery_service, "discover_hosts", fake_discover)
    response = client.post(
        "/api/network/scan", json={"network_cidr": "192.168.1.0/24", "confirm_authorized": True}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["discovered_count"] == 2
    assert payload["devices"][1]["hostname"] is None
    assert payload["devices"][1]["mac_address"] is None
    assert payload["devices"][1]["observation"] == "no_icmp_response"
    assert "Partial observation warning" in payload["warnings"]

    devices = client.get("/api/devices").json()
    assert devices["total"] == 2
    detail = client.get(f"/api/devices/{payload['devices'][1]['id']}").json()
    assert detail["hostname"] is None
    assert detail["latest_observation"] == "no_icmp_response"


def test_ping_endpoint_returns_calculated_statistics(client, db_session, device, monkeypatch):
    results = [
        ProbeResult(True, 10.0),
        ProbeResult(False, None, "timeout"),
        ProbeResult(True, 20.0),
        ProbeResult(True, 30.0),
        ProbeResult(False, None, "timeout"),
    ]
    monkeypatch.setattr(connectivity_service, "ping_once", lambda ip, timeout: results.pop(0))
    response = client.post(f"/api/devices/{device.id}/ping", json={"count": 5, "timeout_ms": 500})
    assert response.status_code == 200
    payload = response.json()
    assert payload["probes_sent"] == 5
    assert payload["probes_received"] == 3
    assert payload["packet_loss_percent"] == 40.0
    assert payload["avg_latency_ms"] == 20.0
    assert payload["min_latency_ms"] == 10.0
    assert payload["max_latency_ms"] == 30.0
    assert payload["jitter_ms"] == 10.0
    assert len(payload["probes"]) == 5
    assert payload["probes"][1]["latency_ms"] is None


def test_device_not_found(client):
    response = client.get("/api/devices/9999")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "DEVICE_NOT_FOUND"


def test_invalid_license_ping_count(client, device):
    response = client.post(f"/api/devices/{device.id}/ping", json={"count": 0})
    assert response.status_code == 422


def test_device_search_and_status_filter(client, db_session):
    first = Device(ip_address="192.168.1.10", hostname="alpha")
    second = Device(ip_address="192.168.1.11", hostname="bravo")
    db_session.add_all([first, second])
    db_session.commit()

    response = client.get("/api/devices", params={"search": "alpha"})
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["ip_address"] == "192.168.1.10"

    response = client.get("/api/devices", params={"status": "not_tested"})
    assert response.json()["total"] == 2


def test_topology_reuses_local_and_gateway_nodes(client, db_session, monkeypatch):
    monkeypatch.setattr(discovery_service.network_info_service, "get_network_info", _network_info)
    db_session.add_all(
        [
            Device(ip_address="192.168.1.35", hostname="this-pc", mac_address="aa:bb:cc:dd:ee:01"),
            Device(ip_address="192.168.1.1", hostname="router", mac_address="aa:bb:cc:dd:ee:02"),
            Device(ip_address="192.168.1.20", hostname="printer"),
        ]
    )
    db_session.commit()

    response = client.get("/api/network/topology")
    assert response.status_code == 200
    payload = response.json()

    assert len([node for node in payload["nodes"] if node["ip_address"] == "192.168.1.35"]) == 1
    assert len([node for node in payload["nodes"] if node["ip_address"] == "192.168.1.1"]) == 1
    local_node = next(node for node in payload["nodes"] if node["id"] == "local-host")
    assert local_node["mac_address"] == "aa:bb:cc:dd:ee:01"
    assert len(payload["nodes"]) == 3
    assert len(payload["edges"]) == 2
