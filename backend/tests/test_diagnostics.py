"""Diagnostic rule tests with matching and non-matching inputs."""

from __future__ import annotations

from datetime import timedelta

from app.database.base import utcnow
from app.models import MonitoringObservation, MonitoringSession, PingTest, SecurityFinding, SecurityScan
from app.services import diagnostics_service


def _session_with(db_session, device, outcomes: list[bool]):
    now = utcnow()
    session = MonitoringSession(
        started_at=now - timedelta(minutes=5), interval_seconds=10, status="stopped", ended_at=now
    )
    db_session.add(session)
    db_session.flush()
    for index, success in enumerate(outcomes):
        db_session.add(
            MonitoringObservation(
                session_id=session.id,
                device_id=device.id,
                observed_at=now - timedelta(minutes=4) + timedelta(seconds=index * 5),
                icmp_success=success,
                latency_ms=10.0 if success else None,
                observation="responding" if success else "no_icmp_response",
            )
        )
    db_session.commit()


def _ping_test(db_session, device, loss: float, avg: float):
    now = utcnow()
    db_session.add(
        PingTest(
            device_id=device.id,
            started_at=now - timedelta(minutes=2),
            completed_at=now,
            probes_sent=10,
            probes_received=10 - int(loss / 10),
            packet_loss_percent=loss,
            avg_latency_ms=avg,
            min_latency_ms=avg / 2,
            max_latency_ms=avg * 2,
            status="completed",
        )
    )
    db_session.commit()


def _security(db_session, device, ports: list[int]):
    now = utcnow()
    scan = SecurityScan(
        device_id=device.id,
        started_at=now - timedelta(minutes=1),
        completed_at=now,
        profile_name="common_services",
        status="completed",
    )
    db_session.add(scan)
    db_session.flush()
    for port in ports:
        db_session.add(
            SecurityFinding(
                security_scan_id=scan.id,
                port=port,
                protocol="tcp",
                state="open",
                service_name="Test",
                severity="review",
                recommendation="Review this service.",
            )
        )
    db_session.commit()


def test_repeated_icmp_failure_rule(db_session, device):
    _session_with(db_session, device, [False, False, False])
    items = diagnostics_service.build_recommendations(db_session, device.id)
    rule = next(item for item in items if item["rule_id"] == "DIAG-REPEATED-ICMP-FAILURE")
    assert rule["severity"] == "warning"
    assert "3 consecutive" in rule["observed_condition"]
    assert rule["evidence"]["consecutive_failures"] == 3


def test_high_packet_loss_rule(db_session, device):
    _ping_test(db_session, device, loss=30.0, avg=20.0)
    items = diagnostics_service.build_recommendations(db_session, device.id)
    rule = next(item for item in items if item["rule_id"] == "DIAG-HIGH-PACKET-LOSS")
    assert "30%" in rule["observed_condition"]
    assert rule["evidence"]["packet_loss_percent"] == 30.0


def test_high_latency_rule(db_session, device):
    _ping_test(db_session, device, loss=0.0, avg=250.0)
    items = diagnostics_service.build_recommendations(db_session, device.id)
    rule = next(item for item in items if item["rule_id"] == "DIAG-HIGH-LATENCY")
    assert "250 ms" in rule["observed_condition"]


def test_telnet_rule(db_session, device):
    _security(db_session, device, [23])
    items = diagnostics_service.build_recommendations(db_session, device.id)
    rule = next(item for item in items if item["rule_id"] == "DIAG-TELNET-OPEN")
    assert "port 23" in rule["observed_condition"]
    assert "not proof of a vulnerability" in rule["recommendation"]


def test_intermittent_connectivity_rule(db_session, device):
    _session_with(db_session, device, [True, False, True, False, True])
    items = diagnostics_service.build_recommendations(db_session, device.id)
    assert any(item["rule_id"] == "DIAG-INTERMITTENT-CONNECTIVITY" for item in items)


def test_healthy_observations_do_not_trigger_warning_rules(db_session, device):
    _session_with(db_session, device, [True] * 5)
    _ping_test(db_session, device, loss=0.0, avg=10.0)
    items = diagnostics_service.build_recommendations(db_session, device.id)
    assert all(item["severity"] != "warning" for item in items)
    assert [item["rule_id"] for item in items] == ["DIAG-NO-DATA"]


def test_no_data_rule(db_session):
    items = diagnostics_service.build_recommendations(db_session)
    assert len(items) == 1
    assert items[0]["rule_id"] == "DIAG-NO-DATA"
    assert items[0]["observed_condition"]


def test_recommendation_history_endpoint(client, db_session, device):
    _ping_test(db_session, device, loss=50.0, avg=300.0)
    response = client.get("/api/diagnostics/recommendations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    rule_ids = {item["rule_id"] for item in payload["items"]}
    assert "DIAG-HIGH-PACKET-LOSS" in rule_ids
    for item in payload["items"]:
        assert item["observed_condition"]
        assert item["recommendation"]
        assert item["created_at"].endswith("Z")
