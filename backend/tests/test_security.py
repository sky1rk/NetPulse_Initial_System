"""Security assessment tests with mocked sockets."""

from __future__ import annotations

import socket

import pytest

from app.services import security_service


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_tcp_open_mapping(monkeypatch):
    monkeypatch.setattr(security_service.socket, "create_connection", lambda *args, **kwargs: FakeConnection())
    assert security_service.check_tcp_port("127.0.0.1", 80, 0.1) == "open"


def test_tcp_refused_mapping(monkeypatch):
    def refused(*args, **kwargs):
        raise ConnectionRefusedError()

    monkeypatch.setattr(security_service.socket, "create_connection", refused)
    assert security_service.check_tcp_port("127.0.0.1", 80, 0.1) == "closed_or_refused"


def test_tcp_timeout_mapping(monkeypatch):
    def timeout(*args, **kwargs):
        raise socket.timeout()

    monkeypatch.setattr(security_service.socket, "create_connection", timeout)
    assert security_service.check_tcp_port("127.0.0.1", 80, 0.1) == "filtered_or_timeout"


def test_tcp_error_mapping(monkeypatch):
    def failure(*args, **kwargs):
        raise OSError(1, "local failure")

    monkeypatch.setattr(security_service.socket, "create_connection", failure)
    assert security_service.check_tcp_port("127.0.0.1", 80, 0.1) == "error"


def test_port_allowlist_rejects_unknown_port():
    with pytest.raises(Exception) as error:
        security_service.validate_ports([9999], None)
    assert getattr(error.value, "code", "") == "PORT_NOT_ALLOWED"


def test_profile_selection():
    ports, label = security_service.validate_ports(None, "web_services")
    assert ports == [80, 443, 8080]
    assert label == "web_services"


def test_unknown_profile_rejected():
    with pytest.raises(Exception) as error:
        security_service.validate_ports(None, "everything")
    assert getattr(error.value, "code", "") == "UNKNOWN_PORT_PROFILE"


def test_authorization_required(db_session, device):
    with pytest.raises(Exception) as error:
        security_service.run_security_scan(db_session, device.id, None, "common_services", False)
    assert getattr(error.value, "code", "") == "AUTHORIZATION_REQUIRED"


def test_scan_persists_all_states(db_session, device, monkeypatch):
    states = {21: "closed_or_refused", 22: "open", 23: "open", 80: "filtered_or_timeout", 443: "open", 3389: "error"}
    monkeypatch.setattr(
        security_service,
        "check_tcp_port",
        lambda ip, port, timeout: states[port],
    )
    scan, findings, warnings = security_service.run_security_scan(
        db_session, device.id, None, "common_services", True
    )
    assert scan.status == "completed"
    assert len(findings) == 6
    by_port = {finding.port: finding for finding in findings}
    assert by_port[22].state == "open"
    assert by_port[21].state == "closed_or_refused"
    assert by_port[80].state == "filtered_or_timeout"
    assert by_port[3389].state == "error"
    assert by_port[23].severity == "review"
    assert "Telnet" in (by_port[23].recommendation or "")
    assert "not proof of a vulnerability" not in (by_port[23].recommendation or "")
    assert warnings == []


def test_no_open_ports_warning(db_session, device, monkeypatch):
    monkeypatch.setattr(security_service, "check_tcp_port", lambda ip, port, timeout: "closed_or_refused")
    scan, findings, warnings = security_service.run_security_scan(
        db_session, device.id, None, "common_services", True
    )
    assert all(finding.state == "closed_or_refused" for finding in findings)
    assert any("does not mean the device is secure" in warning for warning in warnings)


def test_api_scan_requires_confirmation(client, device):
    response = client.post(
        "/api/security/scan",
        json={"device_id": device.id, "ports": [80], "confirm_authorized": False},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AUTHORIZATION_REQUIRED"


def test_api_scan_rejects_disallowed_port(client, device):
    response = client.post(
        "/api/security/scan",
        json={"device_id": device.id, "ports": [1433], "confirm_authorized": True},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "PORT_NOT_ALLOWED"


def test_api_scan_returns_cautious_findings(client, device, monkeypatch):
    monkeypatch.setattr(security_service, "check_tcp_port", lambda ip, port, timeout: "open")
    response = client.post(
        "/api/security/scan",
        json={"device_id": device.id, "ports": [23, 80], "confirm_authorized": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["disclaimer"] == "An open port is an observation, not proof of a vulnerability."
    assert {finding["state"] for finding in payload["findings"]} == {"open"}
    telnet = next(finding for finding in payload["findings"] if finding["port"] == 23)
    assert telnet["severity"] == "review"
    assert "secure alternative" in telnet["recommendation"]
