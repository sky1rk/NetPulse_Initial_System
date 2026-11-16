"""Connectivity parsing and persistence tests."""

from __future__ import annotations

import subprocess

import pytest

from app.models import PingProbe, PingTest
from app.services import connectivity_service
from app.services.connectivity_service import ProbeResult, execute_ping_test, parse_latency_ms


def test_parse_windows_latency():
    assert parse_latency_ms("Reply from 192.168.1.1: bytes=32 time=2ms TTL=64") == 2.0
    assert parse_latency_ms("Reply from 192.168.1.1: bytes=32 time<1ms TTL=64") == 1.0


def test_parse_linux_latency():
    assert parse_latency_ms("64 bytes from 1.1.1.1: icmp_seq=1 ttl=57 time=12.4 ms") == 12.4
    assert parse_latency_ms("no timing information") is None


def test_command_is_argument_list():
    command = connectivity_service.build_ping_command("192.168.1.1", 1000, count=1)
    assert "192.168.1.1" in command
    assert all(isinstance(part, str) for part in command)


def test_partial_loss_and_latency(db_session, device, monkeypatch):
    results = [
        ProbeResult(True, 10.0),
        ProbeResult(False, None, "timeout"),
        ProbeResult(True, 20.0),
        ProbeResult(True, 30.0),
        ProbeResult(False, None, "timeout"),
    ]
    monkeypatch.setattr(connectivity_service, "ping_once", lambda ip, timeout: results.pop(0))
    result = execute_ping_test(db_session, device, count=5, timeout_ms=500)

    test = result["test"]
    assert test.probes_sent == 5
    assert test.probes_received == 3
    assert test.packet_loss_percent == 40.0
    assert test.avg_latency_ms == 20.0
    assert test.min_latency_ms == 10.0
    assert test.max_latency_ms == 30.0
    assert result["jitter_ms"] == 10.0
    assert db_session.query(PingProbe).count() == 5


def test_all_timeouts_store_null_latency(db_session, device, monkeypatch):
    monkeypatch.setattr(
        connectivity_service, "ping_once", lambda ip, timeout: ProbeResult(False, None, "timeout")
    )
    result = execute_ping_test(db_session, device, count=5, timeout_ms=250)

    test = result["test"]
    assert test.packet_loss_percent == 100.0
    assert test.avg_latency_ms is None
    assert test.min_latency_ms is None
    assert test.max_latency_ms is None
    probes = db_session.query(PingProbe).all()
    assert len(probes) == 5
    assert all(probe.latency_ms is None for probe in probes)
    assert result["jitter_ms"] is None
    assert "does not prove" in (result["message"] or "")


def test_subprocess_timeout_maps_to_failure(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr(connectivity_service.subprocess, "run", fake_run)
    result = connectivity_service.ping_once("192.168.1.1", 200)
    assert result.success is False
    assert result.latency_ms is None


def test_missing_ping_utility(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ping")

    monkeypatch.setattr(connectivity_service.subprocess, "run", fake_run)
    with pytest.raises(connectivity_service.PingUtilityUnavailable):
        connectivity_service.ping_once("192.168.1.1", 200)


def test_bounds_are_enforced(db_session, device):
    with pytest.raises(Exception) as error:
        execute_ping_test(db_session, device, count=0, timeout_ms=1000)
    assert getattr(error.value, "code", "") == "INVALID_PROBE_COUNT"

    with pytest.raises(Exception) as error:
        execute_ping_test(db_session, device, count=1000, timeout_ms=1000)
    assert getattr(error.value, "code", "") == "INVALID_PROBE_COUNT"

    with pytest.raises(Exception) as error:
        execute_ping_test(db_session, device, count=1, timeout_ms=999999)
    assert getattr(error.value, "code", "") == "INVALID_TIMEOUT"
